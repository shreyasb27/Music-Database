from typing import Tuple, List, Set

def clear_database(mydb):
    """
    Fully clears all tables in the database in correct child → parent order
    and safely handles foreign key constraints.

    Args:
        mydb: database connection
    """
    cursor = mydb.cursor()

    # Show current rating count (optional for debugging)
    cursor.execute("SELECT COUNT(*) FROM Rating")
    print("Ratings before load:", cursor.fetchone()[0])

    # Disable foreign key checks for safe deletion
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")

    # Delete all rows in child → parent order
    tables = [
        "Rating",
        "Song_genre",
        "Song",
        "Album",
        "User",
        "Genre",
        "Artist"
    ]
    for table in tables:
        cursor.execute(f"DELETE FROM {table};")

    # Commit all deletions
    mydb.commit()

    # Re-enable foreign key checks
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
    cursor.close()

    
def load_single_songs(mydb, single_songs: List[Tuple[str, Tuple[str, ...], str, str]]) -> Set[Tuple[str,str]]:
    """Add single songs to the database. 
    Args:
        mydb: database connection
        single_songs: List of single songs to add. Each single song is a tuple of the form:
              (song title, genre names, artist name, release date)
        Genre names is a tuple since a song could belong to multiple genres
        Release date is of the form yyyy-dd-mm
        Example 1 single song: ('S1',('Pop',),'A1','2008-10-01') => here song is of genre Pop
        Example 2 single song: ('S2',('Rock', 'Pop'),'A2','2000-02-15') => here song is of genre Rock and Pop
    Returns:
        Set[Tuple[str,str]]: set of (song,artist) for combinations that already exist 
        in the database and were not added (rejected). 
        Set is empty if there are no rejects.
    """
    cursor = mydb.cursor()
    rejected = set()

    for title, genre_names, artist_name, release_date in single_songs:
        artist_name = artist_name.strip()
        title = title.strip()

        # VALIDATION: Every song must be in at least one genre
        if not genre_names or len(genre_names) == 0:
            rejected.add((title, artist_name))
            continue

        # In both functions, replace the artist handling with:
        cursor.execute("SELECT artist_id FROM Artist WHERE name = %s", (artist_name,))
        row = cursor.fetchone()
        if row:
            artist_id = row[0]
            # Don't update is_group - use whatever was set before
        else:
            # New artist - use a default value (0 seems reasonable as default)
            cursor.execute("INSERT INTO Artist (name, is_group) VALUES (%s, 0)", (artist_name,))
            artist_id = cursor.lastrowid

        # Check if song already exists for same artist
        cursor.execute("SELECT song_id FROM Song WHERE artist_id = %s AND title = %s", 
                       (artist_id, title))
        if cursor.fetchone():
            rejected.add((title, artist_name))
            continue

        # Insert the song as a single (album_id is NULL, has single_release_date)
        cursor.execute(
            "INSERT INTO Song (artist_id, title, album_id, single_release_date) VALUES (%s, %s, NULL, %s)",
            (artist_id, title, release_date)
        )
        song_id = cursor.lastrowid

        # Insert all genres for this song
        for g in genre_names:
            g = g.strip()
            
            # Ensure genre exists
            cursor.execute("SELECT genre_id FROM Genre WHERE name = %s", (g,))
            g_row = cursor.fetchone()
            if g_row:
                genre_id = g_row[0]
            else:
                cursor.execute("INSERT INTO Genre (name) VALUES (%s)", (g,))
                genre_id = cursor.lastrowid
            
            # Link song to genre
            cursor.execute("INSERT INTO Song_genre (song_id, genre_id) VALUES (%s, %s)", 
                          (song_id, genre_id))

    mydb.commit()
    cursor.close()
    return rejected

def get_most_prolific_individual_artists(mydb, n: int, year_range: Tuple[int,int]) -> List[Tuple[str,int]]:   
    """Get the top n most prolific individual artists by number of singles released in a year range. Break ties by alphabetical order of artist name.
    Args:
        mydb: database connection
        n: how many to get
        year_range: tuple, e.g. (2015,2020)
    Returns:
        List[Tuple[str,int]]: list of (artist name, number of songs) tuples.
        If there are fewer than n artists, all of them are returned.
        If there are no artists, an empty list is returned.
    """
    cursor = mydb.cursor()
    query = """
        SELECT a.name, COUNT(s.song_id) AS num_singles
        FROM Artist a
        JOIN Song s ON a.artist_id = s.artist_id
        WHERE a.is_group = 0
          AND s.album_id IS NULL
          AND YEAR(s.single_release_date) BETWEEN %s AND %s
        GROUP BY a.artist_id
        ORDER BY num_singles DESC, a.name ASC
        LIMIT %s;
    """
    cursor.execute(query, (year_range[0], year_range[1], n))
    result = cursor.fetchall()
    cursor.close()
    return [(row[0], row[1]) for row in result]

def get_artists_last_single_in_year(mydb, year: int) -> Set[str]:
    """
    Get all artists who released their last single in the given year.
    Args:
        mydb: database connection
        year: year of last release
    Returns:
        Set[str]: set of artist names
        If there is no artist with a single released in the given year, an empty set is returned.
    """
    cursor = mydb.cursor()
    query = """
        SELECT a.name
        FROM Artist a
        JOIN Song s ON a.artist_id = s.artist_id
        WHERE s.album_id IS NULL
        GROUP BY a.artist_id
        HAVING MAX(YEAR(s.single_release_date)) = %s;
    """
    cursor.execute(query, (year,))
    result = cursor.fetchall()
    cursor.close()
    return set(row[0] for row in result)
    

from typing import List, Tuple, Set

def load_albums(mydb, albums: List[Tuple[str,str,str,str,List[str]]]) -> Set[Tuple[str,str]]:
    """
    Add albums to the database. 
    
    Args:
        mydb: database connection
        
        albums: List of albums to add. Each album is a tuple of the form:
              (album title, genre, artist name, release date, list of song titles) 
        Release date is of the form yyyy-dd-mm
        Example album: ('Album1','Jazz','A1','2008-10-01',['s1','s2','s3','s4','s5','s6'])

    Returns:
        Set[Tuple[str,str]: set of (album, artist) combinations that were not added (rejected) 
        because the artist already has an album of the same title.
        Set is empty if there are no rejects.
    """
    cursor = mydb.cursor()
    rejected = set()

    for title, genre_name, artist_name, release_date, songs in albums:
        title = title.strip()
        genre_name = genre_name.strip()
        artist_name = artist_name.strip()

        # Reject empty album
        if not songs:
            rejected.add((title, artist_name))
            continue

        # Remove duplicate songs within album
        songs = [s.strip() for s in songs]
        songs = list(dict.fromkeys(songs))

        # Get or create artist
        cursor.execute("SELECT artist_id FROM Artist WHERE name = %s", (artist_name,))
        row = cursor.fetchone()
        artist_id = row[0] if row else None
        if artist_id is None:
            cursor.execute("INSERT INTO Artist (name, is_group) VALUES (%s, 0)", (artist_name,))
            artist_id = cursor.lastrowid

        # Reject duplicate album title for same artist
        cursor.execute("SELECT album_id FROM Album WHERE title = %s AND artist_id = %s", (title, artist_id))
        if cursor.fetchone():
            rejected.add((title, artist_name))
            continue

        # Get or create genre
        cursor.execute("SELECT genre_id FROM Genre WHERE name = %s", (genre_name,))
        row = cursor.fetchone()
        genre_id = row[0] if row else None
        if genre_id is None:
            cursor.execute("INSERT INTO Genre (name) VALUES (%s)", (genre_name,))
            genre_id = cursor.lastrowid

        # Pre-check songs - reject if ANY song already exists for this artist
        reject_album = False
        for song_title in songs:
            cursor.execute("SELECT song_id FROM Song WHERE title = %s AND artist_id = %s", (song_title, artist_id))
            if cursor.fetchone():
                # Song already exists (as single or in another album) → reject
                reject_album = True
                break
        
        if reject_album:
            rejected.add((title, artist_name))
            continue

        # Insert album
        cursor.execute("INSERT INTO Album (title, genre_id, artist_id, release_date) VALUES (%s, %s, %s, %s)",
                       (title, genre_id, artist_id, release_date))
        album_id = cursor.lastrowid

        # Insert all songs (all are new at this point due to pre-check)
        for song_title in songs:
            cursor.execute("INSERT INTO Song (title, artist_id, album_id, single_release_date) VALUES (%s, %s, %s, NULL)",
                           (song_title, artist_id, album_id))
            song_id = cursor.lastrowid
            cursor.execute("INSERT INTO Song_genre (song_id, genre_id) VALUES (%s, %s)", (song_id, genre_id))

    mydb.commit()
    cursor.close()
    return rejected

def get_top_song_genres(mydb, n: int) -> List[Tuple[str,int]]:
    """
    Get n genres that are most represented in terms of number of songs in that genre.
    Songs include singles as well as songs in albums. 
    
    Args:
        mydb: database connection
        n: number of genres

    Returns:
        List[Tuple[str,int]]: list of tuples (genre,number_of_songs), from most represented to
        least represented genre. If number of genres is less than n, returns all.
        Ties broken by alphabetical order of genre names.
    """
    cursor = mydb.cursor()
    query = """
        SELECT g.name, COUNT(sg.song_id) AS num_songs
        FROM Genre g
        JOIN Song_genre sg ON g.genre_id = sg.genre_id
        GROUP BY g.genre_id
        ORDER BY num_songs DESC, g.name ASC
        LIMIT %s;
    """
    cursor.execute(query, (n,))
    result = cursor.fetchall()
    cursor.close()
    return [(row[0], row[1]) for row in result]

def get_album_and_single_artists(mydb) -> Set[str]:
    """Get artists who have released albums as well as singles.
    Args:
        mydb: database connection
    Returns:
        Set[str]: set of artist names
    """
    cursor = mydb.cursor()
    query = """
        SELECT a.name
        FROM Artist a
        WHERE a.artist_id IN (
            SELECT DISTINCT artist_id FROM Album
        ) AND a.artist_id IN (
            SELECT DISTINCT artist_id FROM Song WHERE album_id IS NULL
        );
    """
    cursor.execute(query)
    result = cursor.fetchall()
    cursor.close()
    return set(row[0] for row in result)

    
def load_users(mydb, users: List[str]) -> Set[str]:
    """Add users to the database. 
    Args:
        mydb: database connection
        users: list of usernames
    Returns:
        Set[str]: set of all usernames that were not added (rejected) because 
        they are duplicates of existing users.
        Set is empty if there are no rejects.
    """
    """Add users to the database."""
    cursor = mydb.cursor()
    rejected = set()

    for username in users:
        username = username.strip()
        
        # Check if user already exists
        cursor.execute("SELECT username FROM User WHERE username = %s", (username,))
        if cursor.fetchone():
            rejected.add(username)
            continue
        
        # Insert new user with current timestamp
        cursor.execute(
            "INSERT INTO User (username, created_at) VALUES (%s, NOW())", 
            (username,)
        )

    mydb.commit()
    cursor.close()
    return rejected

   # pass

def load_song_ratings(mydb, song_ratings: List[Tuple[str, Tuple[str,str], int, str]]) -> Set[Tuple[str,str,str]]:
    """
    Load ratings for songs, which are either singles or songs in albums. 

    Args:
        mydb: database connection
        song_ratings: list of rating tuples of the form:
            (rater, (artist, song), rating, date)
        
        The rater is a username, the (artist,song) tuple refers to the uniquely identifiable song to be rated.
        e.g. ('u1',('a1','song1'),4,'2021-11-18') => u1 is giving a rating of 4 to the (a1,song1) song.

    Returns:
        Set[Tuple[str,str,str]]: set of (username,artist,song) tuples that are rejected, for any of the following
        reasons:
        (a) username (rater) is not in the database, or
        (b) username is in database but (artist,song) combination is not in the database, or
        (c) username has already rated (artist,song) combination, or
        (d) everything else is legit, but rating is not in range 1..5
        
        An empty set is returned if there are no rejects.  
    """
    cursor = mydb.cursor()
    rejected = set()

    for username, (artist_name, song_title), rating, rating_date in song_ratings:
        artist_name = artist_name.strip()
        song_title = song_title.strip()
        username = username.strip()

        # VALIDATION (d): Check rating is in valid range 1-5
        if rating < 1 or rating > 5:
            rejected.add((username, artist_name, song_title))
            continue

        # VALIDATION (a): Check if user exists
        cursor.execute("SELECT username FROM User WHERE username = %s", (username,))
        if not cursor.fetchone():
            rejected.add((username, artist_name, song_title))
            continue

        # VALIDATION (b): Check if (artist, song) combination exists
        cursor.execute("""
            SELECT s.song_id 
            FROM Song s 
            JOIN Artist a ON s.artist_id = a.artist_id 
            WHERE s.title = %s AND a.name = %s
        """, (song_title, artist_name))
        
        row = cursor.fetchone()
        if not row:
            rejected.add((username, artist_name, song_title))
            continue

        song_id = row[0]

        # VALIDATION (c): Check if user has already rated this song
        # NOTE: Fixed - removed rating_date check per assignment spec
        # User can only rate a song ONCE, regardless of date
        cursor.execute(
            "SELECT * FROM Rating WHERE username = %s AND song_id = %s",
            (username, song_id)
        )
        if cursor.fetchone():
            rejected.add((username, artist_name, song_title))
            continue

        # All validations passed - insert the rating
        cursor.execute(
            "INSERT INTO Rating (username, song_id, rating_date, rating) VALUES (%s, %s, %s, %s)",
            (username, song_id, rating_date, rating)
        )

    mydb.commit()
    cursor.close()
    return rejected

def get_most_rated_songs(mydb, year_range: Tuple[int,int], n: int) -> List[Tuple[str,str,int]]:
    """Get the top n most rated songs in the given year range (both inclusive), ranked from most rated to least rated. 
    "Most rated" refers to number of ratings, not actual rating scores. 
    Ties are broken in alphabetical order of song title. If the number of rated songs is less
    than n, all rated songs are returned.
    Args:
        mydb: database connection
        year_range: range of years, e.g. (2018-2021), during which ratings were given
        n: number of most rated songs

    Returns:
        List[Tuple[str,str,int]]: list of (song title, artist name, number of ratings for song)   
    """
    cursor = mydb.cursor()
    query = """
        SELECT s.title, ar.name, COUNT(r.rating) AS num_ratings
        FROM Rating r
        JOIN Song s ON r.song_id = s.song_id
        JOIN Artist ar ON s.artist_id = ar.artist_id
        WHERE YEAR(r.rating_date) BETWEEN %s AND %s
        GROUP BY s.song_id
        ORDER BY num_ratings DESC, s.title ASC
        LIMIT %s;
    """
    cursor.execute(query, (year_range[0], year_range[1], n))
    result = cursor.fetchall()
    cursor.close()
    return [(row[0], row[1], row[2]) for row in result]

def get_most_engaged_users(mydb, year_range: Tuple[int,int], n: int) -> List[Tuple[str,int]]:
    """Get the top n most engaged users, in terms of number of songs they have rated. Break ties by alphabetical order of usernames.
    Args:
        mydb: database connection
        year_range: range of years, e.g. (2018-2021), during which ratings were given
        n: number of users

    Returns:
        List[Tuple[str, int]]: list of (username,number_of_songs_rated) tuples
    """
    cursor = mydb.cursor()
    query = """
        SELECT u.username, COUNT(r.song_id) AS num_ratings
        FROM User u
        JOIN Rating r ON u.username = r.username
        WHERE YEAR(r.rating_date) BETWEEN %s AND %s
        GROUP BY u.username
        ORDER BY num_ratings DESC, u.username ASC
        LIMIT %s;
    """
    cursor.execute(query, (year_range[0], year_range[1], n))
    result = cursor.fetchall()
    cursor.close()
    return [(row[0], row[1]) for row in result]

