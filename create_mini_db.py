import argparse
import os
import re
import shutil
import sqlite3
from collections import defaultdict


def rearrange_based_on_comma(name_str):
    """Convert Χατζηγεωργίου, Γιώργος to Γιώργος Χατζηγεωργίου"""
    name_parts = name_str.strip().split(", ")
    if len(name_parts) == 2:
        return f"{name_parts[1]} {name_parts[0]}"
    else:
        # Return the input as is if it doesn't match the expected format
        return name_str.strip()


def format_name(name, person):
    """Reformat name; ignore parentheses"""
    if not name:
        print("personName is empty", person)
        return name
    # Split the name into parts
    parts = re.split(r"(\([^)]*\))", name)
    # Rearrange the parts that are not within parentheses
    rearranged_parts = [
        rearrange_based_on_comma(part) for part in parts if not part.startswith("(")
    ]
    rearranged_name = " ".join(rearranged_parts)
    return rearranged_name


def has_entries_in_table(cursor, table_name, foreign_key_column, foreign_key_value):
    """Checks if the specified table has entries with the given foreign key value"""
    get_only_published = (
        "AND published == 1"
        if table_name
        not in [
            "contributors",
            "authors",
            "actors",
            "costumesPlays",
            "playWorks",
            "playPrograms",
            "postersPlays",
        ]
        else ""
    )
    cursor.execute(
        f"SELECT 1 FROM {table_name} WHERE {foreign_key_column} = ? {get_only_published}",
        (foreign_key_value,),
    )
    return cursor.fetchone() is not None


def convert_article_format(input_str):
    """The playTitles are in the following format: 'τραγούδι της κούνιας – Ζητείται υπηρέτης#Το'
    Make sure to move the article to the beginning of the string"""
    parts = input_str.split("#", 1)  # Split at most once
    if len(parts) == 1:
        title = parts[0].strip()
    else:
        title = f"{parts[1].strip()} {parts[0].strip()}"
    return title


def remove_prefix(company_str, prefix_to_remove="Εθνικό Θέατρο: "):
    """Current company list:
    Εθνικό Θέατρο: Κεντρική Σκηνή
    Εθνικό Θέατρο: Κινητή Μονάδα
    Εθνικό Θέατρο: Νέα Σκηνή
    Εθνικό Θέατρο: Άρμα Θέσπιδος (Κινητή μονάδα Ο.Κ.Θ.Ε.)
    Εθνικό Θέατρο: Απογευματινή Σκηνή
    Εθνικό Θέατρο: Παιδικό Στέκι
    Εθνικό Θέατρο: Πειραματική Σκηνή
    Εθνικό Θέατρο: Άρμα Θέσπιδος
    Εθνικό Θέατρο: -
    Εθνικό Θέατρο: Δευτέρα Σκηνή
    Εθνικό Θέατρο: Α΄ Άρμα Θέσπιδος
    Εθνικό Θέατρο: Τρίτη Σκηνή
    Εθνικό Θέατρο: Δραματική Σκηνή
    Εθνικό Θέατρο: Κεντρική Σκηνή (Παιδική Σκηνή)
    Εθνικό Θέατρο: Πρωτοποριακή Σκηνή
    Εθνικό Θέατρο: Δεύτερη Σκηνή

    Remove the prefix "Εθνικό Θέατρο:" because the LLM only queries the first one.
    """
    return company_str.replace(prefix_to_remove, "", 1)


def create_minidb_schema(cursor_mini):
    # Create the necessary tables in the mini database
    """
    # NOTE: I removed playType because it's currently mostly empty or contains one
    # of the following 2: Ενιαία παράσταση, Δραματουργική σύνθεση
    NOTE 1: renamed playCompany to stageName because it contains
    the following information:
    Εθνικό Θέατρο: Κεντρική Σκηνή
    Εθνικό Θέατρο: Κινητή Μονάδα
    Εθνικό Θέατρο: Νέα Σκηνή
    Εθνικό Θέατρο: Άρμα Θέσπιδος (Κινητή μονάδα Ο.Κ.Θ.Ε.)
    Εθνικό Θέατρο: Απογευματινή Σκηνή
    Εθνικό Θέατρο: Παιδικό Στέκι
    Εθνικό Θέατρο: Πειραματική Σκηνή
    Εθνικό Θέατρο: Άρμα Θέσπιδος
    Εθνικό Θέατρο: -
    Εθνικό Θέατρο: Δευτέρα Σκηνή
    Εθνικό Θέατρο: Α΄ Άρμα Θέσπιδος
    Εθνικό Θέατρο: Τρίτη Σκηνή
    Εθνικό Θέατρο: Δραματική Σκηνή
    Εθνικό Θέατρο: Κεντρική Σκηνή (Παιδική Σκηνή)
    Εθνικό Θέατρο: Πρωτοποριακή Σκηνή
    Εθνικό Θέατρο: Δεύτερη Σκηνή

    2. I will remove stageName (stageName TEXT NULL) for now, it seems to only
    confuse the queries. For instance,
    "έργα που ανέβηκαν στο ΕΘ" queries for "Εθνικό Θέατρο: Κεντρική Σκηνή" only.
    3. Removed playGenre because it only contains the following (scarce) information:
    "Μιούζικαλ", "Αρχαίο δράμα: Τραγωδία"
    """
    cursor_mini.execute(
        """
        CREATE TABLE IF NOT EXISTS plays (
            playID INTEGER PRIMARY KEY,
            playTitle TEXT NOT NULL,
            playURL TEXT URL,
            venue TEXT NULL,
            venueCountry TEXT NULL,
            yearStarted INTEGER,
            yearEnded INTEGER,
            directorID INTEGER,
            photosURL TEXT NULL,
            publicationsURL TEXT NULL,
            programsURL TEXT NULL,
            soundsURL TEXT NULL,
            videosURL TEXT NULL,
            musicSheetsURL TEXT NULL,
            costumesURL TEXT NULL,
            postersURL TEXT NULL
        )
        """
    )

    cursor_mini.execute(
        """
        CREATE TABLE IF NOT EXISTS works (
            workID INTEGER PRIMARY KEY,
            workTitle TEXT NOT NULL,
            workTitleOriginal TEXT NULL,
            workGenre TEXT NULL,
            workLanguage TEXT NULL,
            workYear TEXT NULL,
            workURL TEXT NULL
        )
        """
    )

    cursor_mini.execute(
        """
        CREATE TABLE IF NOT EXISTS playworks (
            playID INTEGER,
            workID INTEGER,
            PRIMARY KEY (playID, workID)
        )
        """
    )

    cursor_mini.execute(
        """
        CREATE TABLE IF NOT EXISTS actors (
            actorID INTEGER PRIMARY KEY,
            playID INTEGER NOT NULL,
            personID INTEGER NOT NULL,
            protagonist INTEGER NULL,
            actorRole TEXT NOT NULL,
            FOREIGN KEY (playID) REFERENCES plays (playID)
            ON DELETE NO ACTION ON UPDATE NO ACTION,
            FOREIGN KEY (personID) REFERENCES people (personID)
            ON DELETE NO ACTION ON UPDATE NO ACTION
        )
    """
    )

    cursor_mini.execute(
        """
        CREATE TABLE authors (
          authorID INTEGER PRIMARY KEY,
          workID INTEGER NOT NULL,
          personID INTEGER NOT NULL,
          FOREIGN KEY (workID) REFERENCES works (workID)
          ON DELETE CASCADE ON UPDATE NO ACTION,
          FOREIGN KEY (personID) REFERENCES people (personID)
          ON DELETE CASCADE ON UPDATE NO ACTION
        )
        """
    )
    cursor_mini.execute(
        """
        CREATE TABLE IF NOT EXISTS people (
            personID INTEGER PRIMARY KEY,
            personName TEXT NULL,
            personCountry TEXT NULL,
            personDateBirth TEXT NULL,
            personDateDeath TEXT NULL,
            personURL TEXT NULL
        )
    """
    )


def create_mini_database(original_db_name, minimal_db_name, base_url):
    """Main script that creates a minimal db from the full SQL schema"""
    base_play_material_link = os.path.join(base_url, "playmaterial/")
    base_play_url = os.path.join(base_url, "play/")
    base_person_url = os.path.join(base_url, "person/")
    base_work_url = os.path.join(base_url, "work/")

    if os.path.exists(minimal_db_name):
        print(
            f"{minimal_db_name} already exists: Add .BK (backup) suffix to existing file"
        )
        shutil.copyfile(minimal_db_name, f"{minimal_db_name}.BK")
        os.remove(minimal_db_name)

    # Connect to the original database
    conn_original = sqlite3.connect(original_db_name)
    cursor_original = conn_original.cursor()

    # Connect to the mini database (creates a new one if not exists)
    conn_mini = sqlite3.connect(minimal_db_name)
    cursor_mini = conn_mini.cursor()

    create_minidb_schema(cursor_mini)

    cursor_original.execute("SELECT personID, relPersonID FROM personToPerson")
    duplicated_people_list = cursor_original.fetchall()
    # The solution below would work if the duplicated ids corresponded to a unique personID:
    # pair_dict = {max(pair): min(pair) for pair in duplicated_people_list}
    # In practice, in at least 2 examples, e.g.:
    # 5774 -> 5439, but 5439 -> 2192, so 5774 should correspond to 2192
    # So we need to ensure that the larger number is they key, and that the value
    # is the lowest possible personID
    pair_dict = defaultdict(list)
    for a, b in duplicated_people_list:
        larger, smaller = (a, b) if a > b else (b, a)
        pair_dict[larger].append(smaller)

    # Now, filter out any smaller number that appears as a key (larger number in any pair)
    # This is done by creating a new dictionary and excluding the duplicates as described
    duplicated_people_dict = {}
    for key, values in pair_dict.items():
        # Include only values that are not keys themselves in the dictionary
        filtered_values = [value for value in values if value not in pair_dict]
        if filtered_values:  # Check if there's any valid value left after filtering
            # We'll only take the first valid value if there's more than one
            duplicated_people_dict[key] = filtered_values[0]

    # Fill in persons table
    cursor_original.execute(
        """SELECT personID, personName, personCountry, personDateBirth, personDateDeath 
        FROM people WHERE published == 1"""
    )
    people_data = cursor_original.fetchall()
    # Exclude duplicated entries by taking into consideration the duplicated_people_dict
    cursor_mini.executemany(
        """INSERT INTO people (personID, personName, personCountry, personDateBirth, 
        personDateDeath, personURL) VALUES (?,?,?,?,?,?)""",
        [
            (
                person[0],
                format_name(person[1], person),
                person[2],
                person[3],
                person[4],
                f"{base_person_url}{person[0]}",
            )
            for person in people_data
            if person[0] not in duplicated_people_dict.keys()
        ],
    )
    # We can also store that info in a dict
    # person_dict = {person[0]: format_name(person[1], person) for person in people_data}

    # List of contributor roles (removed: 'Βοηθός σκηνοθέτη')
    contributor_info = {}
    roles = [
        "Σκηνογραφία",
        "Ενδυματολόγος",
        "Σκηνοθεσία",
        "Μουσική επιμέλεια",
        "Συνθέτης",
        "Χορογραφία",
        "Χορογράφος",
    ]
    # No "published" column
    query = """SELECT playID, personID, contributorType 
    FROM contributors WHERE contributorType IN ({seq})"""
    query = query.format(seq=",".join(["?"] * len(roles)))
    cursor_original.execute(query, roles)
    rows = cursor_original.fetchall()
    for row in rows:
        playID, personID, contributorType = row
        if playID not in contributor_info:
            contributor_info[playID] = {}
        if contributorType == "Χορογράφος":
            # fix duplicated info
            contributorType = "Χορογραφία"
        contributor_info[playID][contributorType] = duplicated_people_dict.get(
            personID, personID
        )
    cursor_original.execute(
        """SELECT workID, workTitle, workTitleOriginal, workGenre, workLanguage, workYear 
        FROM works WHERE published == 1"""
    )
    work_data = cursor_original.fetchall()
    for row in work_data:
        cursor_mini.execute(
            """
            INSERT INTO works (
                workID, workTitle, workTitleOriginal, workGenre, workLanguage, workYear, workURL
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                row[0],
                convert_article_format(row[1]),
                row[2],
                row[3],
                row[4],
                row[5],
                f"{base_work_url}{row[0]}",
            ),
        )
    # Copy relevant data from the original database to the mini database
    cursor_original.execute(
        """
        SELECT
            playID,
            MIN(repeatPeriod1) AS min_repeat_period,
            MAX(repeatPeriod2) AS max_repeat_period
        FROM repeats
        WHERE repeats.published == 1
        GROUP BY playID;
        """
    )
    playrepeats_data = cursor_original.fetchall()

    playrepeats_dict = {}
    for row in playrepeats_data:
        play_id = row[0]
        min_repeat_period = row[1]
        max_repeat_period = row[2]
        playrepeats_dict[play_id] = {"min": min_repeat_period, "max": max_repeat_period}

    # No "published" column
    cursor_original.execute("SELECT workID, playID FROM playWorks")
    playworks_data = cursor_original.fetchall()
    for row in playworks_data:
        cursor_mini.execute("INSERT INTO playWorks (workID, playID) VALUES (?, ?)", row)

    # playworks_map = dict(playworks_data)

    # No "published" column
    cursor_original.execute("SELECT workID, personID from authors")
    authors_data = cursor_original.fetchall()
    for i, row in enumerate(authors_data):
        try:
            # playID or workID? If playID: playworks_map[row[0]]
            cursor_mini.execute(
                """
                INSERT INTO authors (
                    authorID, workID, personID
                ) VALUES (?, ?, ?)
                """,
                (i, row[0], duplicated_people_dict.get(row[1], row[1])),
            )
        except KeyError:
            continue

    cursor_original.execute(
        """
        SELECT r.playID, o.orgName, o.orgCountry
        FROM organizations o
        JOIN repeatsOrgs ro ON o.orgID = ro.orgID
        JOIN repeats r ON ro.repeatID = r.repeatID
        WHERE o.published == 1
        ORDER BY r.playID
        """
    )
    organization_data = cursor_original.fetchall()
    organization_dict = {}
    for row in organization_data:
        play_id = row[0]
        org_name = row[1]
        org_country = row[2]
        if play_id not in organization_dict:
            organization_dict[play_id] = {
                "venues": org_name,
                "venue_countries": org_country,
            }
        else:
            # we allow multiple venues, separated by #
            if org_name not in organization_dict[play_id]["venues"]:
                organization_dict[play_id]["venues"] += f" # {org_name}"
            if org_country not in organization_dict[play_id]["venue_countries"]:
                organization_dict[play_id]["venue_countries"] += f" # {org_country}"

    cursor_original.execute(
        "SELECT playID, playTitle, relatedPlayID FROM plays WHERE published == 1"
    )
    plays_data = cursor_original.fetchall()
    # Loop through each row of the original 'plays' table
    for row in plays_data:
        play_id = row[0]
        play_title = row[1]
        related_play_id = row[2]
        if related_play_id:
            # Το πεδίο relatedPlayID είναι για παραστάσεις που αποτελούν επανάληψη προγενέστερης
            # παράστασης. Νεα λειτουργικότητα που δεν έχει ακόμα χρησιμοποιηθεί.
            # Οι παραστάσεις που δεν έχουν τιμή στο πεδίο αυτό είναι αυτόνομες.
            # What should we do with this info? Perhaps update the
            # original play_id and modify the end date? Or leave as is?
            print(f"playID: {play_id}, Related playID: {related_play_id}")
        # Check if the original database has entries in the corresponding tables
        # has_material = (1
        #                 if has_entries_in_table(cursor_original, "materials", "playID", play_id)
        #                 else 0)
        # hasMaterial INTEGER NULL: από ποιο table γίνεται informed?
        # hasMusicSheet: δεν έχει playID?
        photos = (
            f"{base_play_material_link}{play_id}#photos"
            if has_entries_in_table(cursor_original, "photos", "playID", play_id)
            else None
        )
        videos = (
            f"{base_play_material_link}{play_id}#videos"
            if has_entries_in_table(cursor_original, "videos", "playID", play_id)
            else None
        )
        programs = (
            f"{base_play_material_link}{play_id}#programs"
            if has_entries_in_table(cursor_original, "playPrograms", "playID", play_id)
            else None
        )
        publications = (
            f"{base_play_material_link}{play_id}#publications"
            if has_entries_in_table(cursor_original, "publications", "playID", play_id)
            else None
        )
        costumes = (
            f"{base_play_material_link}{play_id}#costumes"
            if has_entries_in_table(cursor_original, "costumesPlays", "playID", play_id)
            else None
        )
        posters = (
            f"{base_play_material_link}{play_id}#posters"
            if has_entries_in_table(cursor_original, "postersPlays", "playID", play_id)
            else None
        )

        music_sheets = (
            f"{base_play_material_link}{play_id}#music"
            if has_entries_in_table(cursor_original, "musicScores", "musicID", play_id)
            else None
        )
        sounds = (
            f"{base_play_material_link}{play_id}#sounds"
            if has_entries_in_table(cursor_original, "sounds", "playID", play_id)
            else None
        )

        # Insert the data into the new 'plays' table in the mini database
        cursor_mini.execute(
            """
            INSERT INTO plays (
                playID, playTitle, playURL, venue, venueCountry,
                yearStarted, yearEnded, directorID,
                photosURL, publicationsURL, programsURL, soundsURL,
                videosURL, musicSheetsURL, costumesURL, postersURL
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                play_id,
                convert_article_format(play_title),
                f"{base_play_url}{play_id}",
                organization_dict.get(play_id, {}).get("venues"),
                organization_dict.get(play_id, {}).get("venue_countries"),
                playrepeats_dict.get(play_id, {}).get("min"),
                playrepeats_dict.get(play_id, {}).get("max"),
                contributor_info.get(play_id, {}).get("Σκηνοθεσία"),
                photos,
                publications,
                programs,
                sounds,
                videos,
                music_sheets,
                costumes,
                posters,
            ),
        )

    cursor_original.execute("SELECT * FROM actors")
    actors_data = cursor_original.fetchall()
    actors_data1 = []
    for i, actor in enumerate(actors_data):
        actors_data1.append(list(actor))
        actors_data1[i][3] = int(str(actors_data1[i][3]) == "1")
    cursor_mini.executemany(
        "INSERT INTO actors (actorID, playID, personID, protagonist, actorRole) VALUES (?,?,?,?,?)",
        [
            (
                actor[0],
                actor[1],
                duplicated_people_dict.get(actor[2], actor[2]),
                actor[3],
                actor[5],
            )
            for actor in actors_data1
        ],
    )

    # Commit the changes and close connections
    conn_mini.commit()
    conn_mini.close()
    conn_original.close()

    print(f"Mini SQLite database ({minimal_db_name}) created successfully.")


def parse_arguments():
    """Parse CLI arguments"""
    parser = argparse.ArgumentParser(
        description="A script that accepts original DB name, minimal DB name, "
        "and base URL as arguments.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "--original-db-name",
        default="converted_db.sqlite",
        help="Original SQLite database name (the output of create_sqlite_db.py)",
    )
    parser.add_argument(
        "--minimal-db-name",
        default="minimal_nt.db",
        help="Mini SQLite database name that will be used by the VA",
    )
    parser.add_argument(
        "--base-url", default="http://194.177.217.106/", help="Base URL"
    )

    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    create_mini_database(args.original_db_name, args.minimal_db_name, args.base_url)
