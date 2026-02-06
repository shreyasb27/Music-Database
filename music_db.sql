
SET FOREIGN_KEY_CHECKS = 0;

-- 1. Artist table
DROP TABLE IF EXISTS `Artist`;
CREATE TABLE `Artist` (
  `artist_id` int NOT NULL AUTO_INCREMENT,
  `name` varchar(200) NOT NULL,
  `is_group` tinyint(1) NOT NULL,
  PRIMARY KEY (`artist_id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4;

INSERT INTO `Artist` VALUES 
(1,'A1',0),
(2,'Band1',1);

-- 2. Genre table
DROP TABLE IF EXISTS `Genre`;
CREATE TABLE `Genre` (
  `genre_id` smallint NOT NULL AUTO_INCREMENT,
  `name` varchar(100) NOT NULL,
  PRIMARY KEY (`genre_id`),
  UNIQUE KEY `name` (`name`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4;

INSERT INTO `Genre` VALUES
(1,'Pop'),
(2,'Rock');

-- 3. Album table
DROP TABLE IF EXISTS `Album`;
CREATE TABLE `Album` (
  `album_id` int NOT NULL AUTO_INCREMENT,
  `artist_id` int NOT NULL,
  `title` varchar(200) NOT NULL,
  `release_date` date NOT NULL,
  `genre_id` smallint NOT NULL,
  PRIMARY KEY (`album_id`),
  UNIQUE KEY `artist_id` (`artist_id`,`title`),
  KEY `genre_id` (`genre_id`),
  CONSTRAINT `album_ibfk_1` FOREIGN KEY (`artist_id`) REFERENCES `Artist` (`artist_id`),
  CONSTRAINT `album_ibfk_2` FOREIGN KEY (`genre_id`) REFERENCES `Genre` (`genre_id`)
) ENGINE=InnoDB AUTO_INCREMENT=2 DEFAULT CHARSET=utf8mb4;

INSERT INTO `Album` VALUES
(1,2,'Album1','2020-01-01',1);

-- 4. User table
DROP TABLE IF EXISTS `User`;
CREATE TABLE `User` (
  `username` varchar(50) NOT NULL,
  `created_at` datetime NOT NULL,
  PRIMARY KEY (`username`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `User` VALUES 
('user1','2025-11-23 20:55:24'),
('user2','2025-11-23 20:55:24');

-- 5. Song table
DROP TABLE IF EXISTS `Song`;
CREATE TABLE `Song` (
  `song_id` int NOT NULL AUTO_INCREMENT,
  `artist_id` int NOT NULL,
  `title` varchar(200) NOT NULL,
  `album_id` int DEFAULT NULL,
  `single_release_date` date DEFAULT NULL,
  PRIMARY KEY (`song_id`),
  UNIQUE KEY `artist_id` (`artist_id`,`title`),
  KEY `album_id` (`album_id`),
  CONSTRAINT `song_ibfk_1` FOREIGN KEY (`artist_id`) REFERENCES `Artist` (`artist_id`),
  CONSTRAINT `song_ibfk_2` FOREIGN KEY (`album_id`) REFERENCES `Album` (`album_id`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4;

INSERT INTO `Song` VALUES
(1,1,'Song1',NULL,'2021-01-01'),
(2,2,'Song2',NULL,'2020-06-15');

-- 6. Song_genre table
DROP TABLE IF EXISTS `Song_genre`;
CREATE TABLE `Song_genre` (
  `song_id` int NOT NULL,
  `genre_id` smallint NOT NULL,
  PRIMARY KEY (`song_id`,`genre_id`),
  KEY `genre_id` (`genre_id`),
  CONSTRAINT `song_genre_ibfk_1` FOREIGN KEY (`song_id`) REFERENCES `Song` (`song_id`),
  CONSTRAINT `song_genre_ibfk_2` FOREIGN KEY (`genre_id`) REFERENCES `Genre` (`genre_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `Song_genre` VALUES
(1,1),
(2,2);

-- 7. Rating table
DROP TABLE IF EXISTS `Rating`;
CREATE TABLE `Rating` (
  `username` varchar(50) NOT NULL,
  `song_id` int NOT NULL,
  `rating_date` date NOT NULL,
  `rating` tinyint NOT NULL,
  PRIMARY KEY (`username`,`song_id`,`rating_date`),
  KEY `song_id` (`song_id`),
  CONSTRAINT `rating_ibfk_1` FOREIGN KEY (`username`) REFERENCES `User` (`username`),
  CONSTRAINT `rating_ibfk_2` FOREIGN KEY (`song_id`) REFERENCES `Song` (`song_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

INSERT INTO `Rating` VALUES
('user1',1,'2021-05-01',5),
('user2',2,'2020-07-01',4);

-- Re-enable foreign key checks
SET FOREIGN_KEY_CHECKS = 1;
