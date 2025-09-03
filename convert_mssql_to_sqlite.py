import argparse
import os
import re
import shutil
import sqlite3
import sys

DEBUG = False
# This dict contains table names that we won't be using in the minimal DB schema
tables_to_ignore = {
    "actorsCostumes",
    "cmslogs",
    "cmsUsers",
    "contributorGroups",
    "costumes",
    "costumesColors",
    "costumesFabrics",
    "costumesGenreColors",
    "costumesGenreFabrics",
    "costumesGenreMaterials",
    "costumesGenrePeriods",
    "costumesGenreTypes",
    "costumesMaterials",
    "costumesParts",
    "costumesPartsColors",
    "costumesPartsMaterials",
    "costumesPartsTypes",
    "costumesTypes",
    "costumesGenreMaterialsGroups",
    "costumesPartsTypesGroups",
    "costumesGenreTypesGroups",
    "costumesGenreTypesGroupID",
    "countries",
    "editors",
    "errorLogs",
    "filesPhotos",
    "filesPrograms",
    "filesPublications",
    "filesSounds",
    "filesVideos",
    "frontUsers",
    "geonames",
    "hisPhotosPhotographers",
    "hisPhotosTopics",
    "hisPhotosTypes",
    "historicPhotos",
    "historicPlaces",
    "historicPlacesPhotos",
    "languages_old",
    "music",
    "musicOrchestrators",
    "musicScoreFiles",
    "musicScoreGenreInstruments",
    "musicScoresInstruments",
    "musicScoresTypes",
    "photosRepeats",
    "photosTypes",
    "photosWorks",
    "plays_new",
    "postersCreators",
    "postersLangs",
    "posters",
    "postersRepeats",
    "programs",
    "programsLangs",
    "programsRepeats",
    "programWorks",
    "pubAuthors",
    "pubMediums",
    "pubsLangs",
    "pubTypes",
    "pubsInDigital",
    "repeatWorks",
    "soundParts",
    "soundTypes",
    "tempPhotoTrans",
    "tempTransActorRoles",
    "tempTransPubs",
    "tempTransHistoricPhotos",
    "tempTransWorks",
    "tempTransPlays",
    "trans",
    "transCopy2",
    "userFavorites",
    "userHistory",
    "videoParts",
    "videoTypes",
    "worksGenreOrigin",
    "worksGenrePeriod",
    "worksGenreType",
    "worksOrigins",
    "worksPeriods",
    "worksTypes",
}


def replace_unicode_strings(input_string):
    """There are some unicode strings in the db; replace them to insert them correctly in SQLite"""
    # Remove the 'N' prefix from all Unicode strings
    result_string = re.sub(r"N'([^']*)'", r"'\1'", input_string)

    return result_string


def replace_cast_string(input_string):
    """Matches CAST dates from MS SQL and converts them to a string"""
    pattern = r"CAST\(N'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+)' AS DateTime\)"
    result_string = re.sub(pattern, r"'\1'", input_string)
    return result_string


def extract_insert_statements(sql_script):
    """Function to extract INSERT statements from SQL Server script"""
    sql_script = replace_cast_string(sql_script)
    sql_script = replace_unicode_strings(sql_script)
    # also remove random Greek question marks
    sql_script = sql_script.replace(" (;)", "")
    pattern = re.compile(
        "INSERT\s+.*?\[dbo\]\.\[([^\]]+)\]\s*\(([^)]*)\).*?VALUES\s\((.*)\)"
    )
    return re.findall(pattern, sql_script)


def correct_newlines(sql_script):
    """This function corrects the extra newlines to have each INSERT statement in one line.
    For instance:
    INSERT [dbo].[sounds] ([soundID], [playID], [workIDstr], [repeatStr], [soundRank], [soundFile],
    [soundDate], [soundPerson], [soundType], [soundTime], [soundCaption], [soundNotes],
    [soundDescription], [soundReviewedFlag], [modified], [created], [published],
    [soundTypeID], [cmsCreatorID])
    VALUES (157, 406, N'6097', N'1032', 1, N'0146-01', N'', N'', N'Πρόβα', N'', N'',
    N'#***# Δεν είναι σίγουρο με ποια παράσταση πρέπει να συνδεθεί. Μου φαίνεται λογικό να το
    συνδέσωμε την πρώτη από αυτή τη σειρά παραστάσεων.', N'Μέρη από το έργο.

    Τρακ 1: Φαίνεται ότι είναι από πρόβα γιατί ακούγονται οδηγίες στην αρχή.
    1) Ορέστης -Κλυταιμνήστρα (652 - 709), 2), 3) 722 - 1065 (τέλος;).
    Τρακ 2: Από την αρχή μέχρι στ.590 (αρχή πρώτου στάσιμου). Αποσπάσματα', 0, NULL,
    CAST(N'2023-03-15T12:48:59.843' AS DateTime), 1, 8, NULL)

    becomes:

    INSERT [dbo].[sounds] ([soundID], [playID], [workIDstr], [repeatStr], [soundRank], [soundFile],
    [soundDate], [soundPerson], [soundType], [soundTime], [soundCaption], [soundNotes],
    [soundDescription], [soundReviewedFlag], [modified], [created], [published],
    [soundTypeID], [cmsCreatorID])
    VALUES (157, 406, N'6097', N'1032', 1, N'0146-01', N'', N'', N'Πρόβα', N'', N'',
    N'#***# Δεν είναι σίγουρο με ποια παράσταση πρέπει να συνδεθεί. Μου φαίνεται λογικό να το
    συνδέσω με την πρώτη από αυτή τη σειρά παραστάσεων.', N'Μέρη από το έργο.  Τρακ 1: Φαίνεται ότι
    είναι από πρόβα γιατί ακούγονται οδηγίες στην αρχή. 1) Ορέστης -Κλυταιμνήστρα (652 - 709), 2),
    3) 722 - 1065 (τέλος;). Τρακ 2: Από την αρχή μέχρι στ.590 (αρχή πρώτου στάσιμου). Αποσπάσματα',
    0, NULL, CAST(N'2023-03-15T12:48:59.843' AS DateTime), 1, 8, NULL)
    """
    lines = sql_script.split("\n")
    processed_lines = []

    for i, line in enumerate(lines):
        # If line starts with 'INSERT' or 'GO', or it's the first line, keep it as is
        if line.startswith("INSERT") or line.startswith("GO") or i == 0:
            processed_lines.append(line)
        else:  # Otherwise, remove the line break
            processed_lines[-1] += " " + line.strip()
    return "\n".join(processed_lines)


def create_sqlite_tables(sqlite_db_name):
    """Create a new sqlite db keeping in mind the MS SQL schema.
    Tables that were ignored from the original schema because they won't be used:
    1. "actorsCostumes": Contrains actorID|costumeID
    2. "contributorGroups": Removed because it only contains the following 2:
        contriGroupID|descr|lexiconURL
        1|Μουσική|
        2|Σκηνοθεσία|
    3. "costumes"; we're only using "costumesPlays"
    4. "countries": Removed because it only contains the name, no IDs
    5. "music": we're only using "musicPlaysWorks"
    """
    # Connect to the new SQLite database
    conn = sqlite3.connect(sqlite_db_name)
    cursor = conn.cursor()

    # Create the "actors" table
    cursor.execute(
        """
        CREATE TABLE actors (
            actorID INTEGER PRIMARY KEY AUTOINCREMENT,
            playID INTEGER NOT NULL,
            personID INTEGER NOT NULL,
            actorRank INTEGER NOT NULL,
            workID INTEGER NULL,
            actorRole TEXT NULL,
            modified DATETIME NULL,
            created DATETIME NOT NULL,
            cmsCreatorID INTEGER NULL
        );
        """
    )
    # Create the "authors" table
    cursor.execute(
        """
        CREATE TABLE authors (
            authorID INTEGER PRIMARY KEY AUTOINCREMENT,
            workID INTEGER NOT NULL,
            personID INTEGER NOT NULL,
            authorRank INTEGER NOT NULL,
            modified DATETIME NULL,
            created DATETIME NOT NULL,
            cmsCreatorID INTEGER NULL
        );
        """
    )
    # Create table "companies"
    cursor.execute(
        """
        CREATE TABLE companies (
            companyID INTEGER PRIMARY KEY AUTOINCREMENT,
            description TEXT NULL,
            published SMALLINT NULL,
            modified DATETIME NULL,
            created DATETIME NULL,
            cmsCreatorID INTEGER NULL
        );
        """
    )
    # Create table "contributors"
    cursor.execute(
        """
        CREATE TABLE contributors (
            contributorsID INTEGER PRIMARY KEY AUTOINCREMENT,
            playID INTEGER NOT NULL,
            personID INTEGER NOT NULL,
            contributorRank INTEGER NOT NULL,
            workID INTEGER NULL,
            contributorType TEXT NULL,
            modified DATETIME NULL,
            created DATETIME NOT NULL,
            contriTypeID INTEGER NULL,
            cmsCreatorID INTEGER NULL
        );
        """
    )
    # Create the "contributorTypes" table
    cursor.execute(
        """
            CREATE TABLE contributorTypes (
                contriTypeID INTEGER PRIMARY KEY AUTOINCREMENT,
                descr TEXT NULL,
                lexiconURL TEXT NULL,
                contriGroupID INTEGER NULL
            );
        """
    )
    # Create the "coproducers" table
    cursor.execute(
        """
        CREATE TABLE coproducers (
            coprodplayID INTEGER PRIMARY KEY AUTOINCREMENT,
            orgID INTEGER NOT NULL,
            playID INTEGER NOT NULL,
            coproducerRank INTEGER NULL,
            cmsCreatorID INTEGER NULL
        );
        """
    )
    # Create the "costumesPlays" table
    cursor.execute(
        """
        CREATE TABLE costumesPlays (
            costumePlayID INTEGER PRIMARY KEY AUTOINCREMENT,
            costumeID INTEGER NOT NULL,
            playID INTEGER NOT NULL
        );
        """
    )
    # Create the "languages" table
    cursor.execute(
        """
        CREATE TABLE languages (
            languageID INTEGER PRIMARY KEY AUTOINCREMENT,
            langtxt TEXT NULL,
            lexiconURL TEXT NULL
        );
        """
    )
    # Create the "musicComposers" table
    cursor.execute(
        """
        CREATE TABLE musicComposers (
            musicComposerID INTEGER PRIMARY KEY AUTOINCREMENT,
            musicID INTEGER NOT NULL,
            personID INTEGER NOT NULL,
            musicComposerRank INTEGER NULL,
            modified DATETIME NULL,
            created DATETIME NOT NULL,
            cmsCreatorID INTEGER NULL
        );
        """
    )
    # Create the "musicGenres" table
    cursor.execute(
        """
        CREATE TABLE musicGenres (
            musicGenreID INTEGER PRIMARY KEY AUTOINCREMENT,
            descr TEXT NULL,
            lexiconURL TEXT NULL
        );
        """
    )
    # Create the "musicPlaysWorks" table
    cursor.execute(
        """
        CREATE TABLE musicPlaysWorks (
            musicID INTEGER NULL,
            playID INTEGER NULL,
            workID INTEGER NULL
        );
        """
    )
    # Create the "musicScores" table
    cursor.execute(
        """
        CREATE TABLE musicScores (
            musicScoreID INTEGER PRIMARY KEY AUTOINCREMENT,
            musicID INTEGER NULL,
            musicScoreRank INTEGER NULL,
            musicScoreFilePrefix VARCHAR(50) NULL,
            musicScoreType NVARCHAR(255) NULL,
            musicScoreTypeID INTEGER NULL,
            musicScoreInstruments NVARCHAR(255) NULL,
            musicScoreDescription NVARCHAR(4000) NULL,
            modified DATETIME NULL,
            created DATETIME NOT NULL,
            published INTEGER NULL,
            cmsCreatorID INTEGER NULL
        );
        """
    )
    # Create the "organizations" table
    cursor.execute(
        """
        CREATE TABLE organizations (
            orgID INTEGER PRIMARY KEY AUTOINCREMENT,
            orgName NVARCHAR(255) NULL,
            orgAddress NVARCHAR(255) NULL,
            orgCity NVARCHAR(255) NULL,
            orgCountry NVARCHAR(255) NULL,
            orgHistory NVARCHAR(255) NULL,
            orgNotes NVARCHAR(3500) NULL,
            modified DATETIME NULL,
            created DATETIME NOT NULL,
            published INTEGER NULL,
            cmsCreatorID INTEGER NULL
        );
        """
    )
    # Create the "people" table
    cursor.execute(
        """
        CREATE TABLE people (
            personID INTEGER PRIMARY KEY AUTOINCREMENT,
            personName NVARCHAR(500) NULL,
            personNameOriginal NVARCHAR(255) NULL,
            personNamesOther NVARCHAR(255) NULL,
            personCountry NVARCHAR(255) NULL,
            personDateBirth VARCHAR(100) NULL,
            personDateDeath VARCHAR(100) NULL,
            personNotes TEXT NULL,
            modified DATETIME NULL,
            created DATETIME NOT NULL,
            edm NVARCHAR(250) NULL,
            published INTEGER NULL,
            cmsCreatorID INTEGER NULL,
            saved SMALLINT,
            lexiconURL NVARCHAR(1000) NULL
        );
        """
    )
    # Create the "photos" table
    cursor.execute(
        """
        CREATE TABLE photos (
            photoID INTEGER PRIMARY KEY AUTOINCREMENT,
            playID INTEGER NULL,
            workIDstr VARCHAR(500) NULL,
            repeatStr VARCHAR(500) NULL,
            photoRank INTEGER NULL,
            photoFile VARCHAR(255) NULL,
            photoDate VARCHAR(100) NULL,
            photographer NVARCHAR(255) NULL,
            photoType NVARCHAR(255) NULL,
            photoTypeID INTEGER NULL,
            hasColor INTEGER NULL,
            photoCaption NVARCHAR(255) NULL,
            photoNotes NVARCHAR(1500) NULL,
            photoDescription NVARCHAR(2000) NULL,
            tech_resolution NVARCHAR(500) NULL,
            tech_depth NVARCHAR(500) NULL,
            tech_dimensions NVARCHAR(500) NULL,
            modified DATETIME NULL,
            created DATETIME NOT NULL,
            published INTEGER NULL,
            cmsCreatorID INTEGER NULL
        );
    """
    )
    # Create the "playPrograms" table
    cursor.execute(
        """
        CREATE TABLE playPrograms (
            playProgramID INTEGER PRIMARY KEY AUTOINCREMENT,
            playID INTEGER NOT NULL,
            programID INTEGER NOT NULL,
            programRank INTEGER NULL,
            repeatStr VARCHAR(500) NULL,
            modified DATETIME NULL,
            created DATETIME NOT NULL,
            cmsCreatorID INTEGER NULL
        );
        """
    )
    # Create the "plays" table
    cursor.execute(
        """
        CREATE TABLE plays (
            playID INTEGER PRIMARY KEY AUTOINCREMENT,
            playTitle NVARCHAR(255) NULL,
            playCompany NVARCHAR(255) NULL,
            playGenre VARCHAR(255) NULL,
            playGenreID INTEGER NULL,
            playType VARCHAR(255) NULL,
            playTypeID INTEGER NULL,
            playNotes NVARCHAR(3000) NULL,
            companyID INTEGER NULL,
            modified DATETIME NULL,
            created DATETIME NOT NULL,
            published SMALLINT NULL,
            cmsCreatorID INTEGER NULL,
            playOrgTemp NVARCHAR(500) NULL,
            playSceneTemp NVARCHAR(500) NULL,
            relatedPlayID INTEGER NULL
        );
        """
    )
    # Create the "playWorks" table
    cursor.execute(
        """
        CREATE TABLE playWorks (
            playWorksID INTEGER PRIMARY KEY AUTOINCREMENT,
            playID INTEGER NOT NULL,
            workID INTEGER NOT NULL,
            workRank INTEGER NOT NULL,
            cmsCreatorID INTEGER NULL
        );
        """
    )
    # Create the "postersPlays" table
    cursor.execute(
        """
        CREATE TABLE postersPlays (
            posterPlayID INTEGER PRIMARY KEY AUTOINCREMENT,
            posterID INTEGER NOT NULL,
            playID INTEGER NOT NULL
        );
        """
    )
    # Create the "producers" table
    cursor.execute(
        """
        CREATE TABLE producers (
            playID INTEGER NOT NULL,
            orgID INTEGER NOT NULL,
            producerRank INTEGER NOT NULL,
            modified DATETIME NULL,
            created DATETIME NOT NULL
        );
        """
    )
    # Create the "publications" table
    cursor.execute(
        """
        CREATE TABLE publications (
            pubID INTEGER PRIMARY KEY AUTOINCREMENT,
            playID INTEGER NULL,
            workIDstr VARCHAR(500) NULL,
            repeatStr VARCHAR(500) NULL,
            pubRank INTEGER NULL,
            pubFile VARCHAR(255) NULL,
            pubTitle NVARCHAR(500) NULL,
            pubDate VARCHAR(255) NULL,
            pubMediumID INTEGER NULL,
            pubName NVARCHAR(255) NULL,
            pubTypeID INTEGER NULL,
            pubColumn NVARCHAR(255) NULL,
            pubPictures VARCHAR(50) NULL,
            isURL SMALLINT NULL,
            pubURL VARCHAR(500) NULL,
            pubNotes NVARCHAR(3500) NULL,
            pubReviewedFlag BOOLEAN NOT NULL,
            modified DATETIME NULL,
            created DATETIME NOT NULL,
            published SMALLINT NULL,
            textcontent TEXT NULL,
            cmsCreatorID INTEGER NULL,
            repeatID INTEGER NULL
        );
        """
    )
    # Create the "repeats" table
    cursor.execute(
        """
        CREATE TABLE repeats (
            repeatID INTEGER PRIMARY KEY AUTOINCREMENT,
            playID INTEGER NOT NULL,
            repeatPeriod1 VARCHAR(50) NULL,
            repeatPeriod2 VARCHAR(50) NULL,
            repeatDateStart VARCHAR(50) NULL,
            repeatDateEnd VARCHAR(50) NULL,
            repeatRank INTEGER NULL,
            repeatNotes NVARCHAR(3500) NULL,
            published SMALLINT NULL,
            modified DATETIME NULL,
            created DATETIME NULL,
            cmsCreatorID INTEGER NULL,
            saved SMALLINT
        );
        """
    )
    # Create the "repeatsOrgs" table
    cursor.execute(
        """
        CREATE TABLE repeatsOrgs (
            repeatID INTEGER NOT NULL,
            orgID INTEGER NOT NULL,
            PRIMARY KEY (repeatID, orgID)
        );
        """
    )
    # Create the "sounds" table
    cursor.execute(
        """
        CREATE TABLE sounds (
            soundID INTEGER PRIMARY KEY AUTOINCREMENT,
            playID INTEGER,
            workIDstr VARCHAR(500),
            repeatStr VARCHAR(500),
            soundRank INTEGER,
            soundFile VARCHAR(255),
            soundDate VARCHAR(100),
            soundPerson NVARCHAR(255),
            soundType NVARCHAR(255),
            soundTime VARCHAR(100),
            soundCaption NVARCHAR(255),
            soundNotes NVARCHAR(1500),
            soundDescription NVARCHAR(2000),
            soundReviewedFlag BOOLEAN NOT NULL,
            modified DATETIME,
            created DATETIME NOT NULL,
            published SMALLINT,
            soundTypeID INTEGER,
            cmsCreatorID INTEGER
        );
        """
    )
    # Create the "translators" table
    cursor.execute(
        """
        CREATE TABLE translators (
            translatorID INTEGER PRIMARY KEY AUTOINCREMENT,
            workID INTEGER NOT NULL,
            personID INTEGER NOT NULL,
            translatorRank INTEGER NOT NULL,
            cmsCreatorID INTEGER
        );
        """
    )
    # Create the "videos" table
    cursor.execute(
        """
        CREATE TABLE videos (
            videoID INTEGER PRIMARY KEY AUTOINCREMENT,
            playID INTEGER,
            workIDstr VARCHAR(255),
            repeatStr VARCHAR(500),
            videoRank INTEGER,
            videoFile VARCHAR(255),
            videoDate VARCHAR(100),
            videoPerson NVARCHAR(255),
            videoType NVARCHAR(255),
            videoTime VARCHAR(100),
            videoCaption NVARCHAR(255),
            videoNotes NVARCHAR(1500),
            videoDescription NVARCHAR(2000),
            videoReviewedFlag BIT NOT NULL,
            modified DATETIME,
            created DATETIME NOT NULL,
            published SMALLINT,
            videoTypeID INTEGER,
            cmsCreatorID INTEGER,
            isURL TINYINT
        );
        """
    )
    # Create the "works" table
    cursor.execute(
        """
        CREATE TABLE works (
            workID INTEGER PRIMARY KEY AUTOINCREMENT,
            workTitle NVARCHAR(255),
            workTitleOriginal NVARCHAR(255),
            workGenre NVARCHAR(255),
            workLanguage NVARCHAR(200),
            workYear NVARCHAR(100),
            workNotes NVARCHAR(3000),
            isTheoritical SMALLINT,
            sourceTheoritical NVARCHAR(1000),
            modified DATETIME,
            created DATETIME NOT NULL,
            published SMALLINT,
            cmsCreatorID INTEGER,
            saved SMALLINT
        );
        """
    )

    cursor.execute(
        """
        CREATE TABLE personToPerson (
            relID INTEGER PRIMARY KEY,
            personID INTEGER NULL,
            relPersonID INTEGER NULL
        );
        """
    )
    # Commit all changes and close the database connection
    conn.commit()
    conn.close()


def parse_arguments():
    """Parse CLI arguments"""
    parser = argparse.ArgumentParser(
        description="Convert SQL Server dump to SQLite",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--sql-server-dump",
        help="Path to the SQL Server dump file",
    )
    parser.add_argument(
        "--sqlite-db",
        default="converted_db.sqlite",
        help="Name of the SQLite database file",
    )
    parser.add_argument(
        "--encoding", default="utf-16-le", help="Encoding of the SQL Server dump file"
    )

    return parser.parse_args()


def insert_db_entries(sqlite_db_name, sql_server_db, encoding):
    """Reads the SQL Server script from a file and
    updates the sqlite db"""
    with open(sql_server_db, "r", encoding=encoding) as sql_file:
        sql_script = sql_file.read()

    # Fix erroneous new lines; all statements should be one-liners
    sql_script = correct_newlines(sql_script)
    # Extract only the INSERT statements from the SQL Server script
    insert_statements = extract_insert_statements(sql_script)
    if not insert_statements:
        sys.exit("No SQL insertions found")

    if DEBUG:
        print("Saving a list of all regex matches to 'insert.txt'")
        with open("insert.txt", "w", encoding="utf-8") as reader:
            for item in insert_statements:
                reader.write(", ".join(map(str, item)) + "\n")

    # Connect to the SQLite database
    conn = sqlite3.connect(sqlite_db_name)
    cursor = conn.cursor()
    num_errors = 0
    # Iterate through INSERT statements and insert data into SQLite
    for table_name, columns, values in insert_statements:
        # Check if the table should be ignored
        if table_name in tables_to_ignore:
            continue
        # Construct the INSERT SQL statement for SQLite
        insert_sql = f"INSERT INTO {table_name} ({columns}) VALUES ({values});"
        try:
            # Execute the INSERT statement
            cursor.execute(insert_sql)
        except sqlite3.OperationalError as e:
            print(e, insert_sql)
            num_errors += 1
            continue

    # Commit changes and close the SQLite database
    conn.commit()
    conn.close()

    print(
        f"Data from SQL Server script ({sql_server_db}) inserted into SQLite database "
        f"({sqlite_db_name})."
    )
    if num_errors:
        print(f"Num errors: {num_errors}/{len(insert_statements)}.")


if __name__ == "__main__":
    args = parse_arguments()

    if os.path.exists(args.sqlite_db):
        # if the minimal db already exists, create a backup file and delete it
        shutil.copyfile(args.sqlite_db, f"{args.sqlite_db}.BK")
        os.remove(args.sqlite_db)

    print("Starting the conversion process")
    create_sqlite_tables(sqlite_db_name=args.sqlite_db)
    insert_db_entries(
        sqlite_db_name=args.sqlite_db,
        sql_server_db=args.sql_server_dump,
        encoding=args.encoding,
    )
