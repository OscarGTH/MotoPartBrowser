import logging
from bs4 import BeautifulSoup
import os
import requests
import psycopg2
from time import sleep
from dotenv import load_dotenv
import datetime


# Custom imports
from constants import (
    IGNORED_LINK_URLS,
    top_motorcycle_brands,
    YEAR_INSERT_QUERY,
    MODEL_INSERT_QUERY,
    BRAND_INSERT_QUERY,
)


# Configure the logging settings
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filename="moto_part_finder.log",
    filemode="w",
    encoding="utf-8",
)

# Creating a logger instance
logger = logging.getLogger("moto_part_finder")

# Valid years for motorcycle models.
min_valid_year = 1970
current_year = datetime.datetime.now().year

"""
Web crawler that reads used motorcycle parts web page and extracts information from it.
"""


class Crawler:
    def __init__(self, url_name: str) -> None:
        # Loading environment variables.
        load_dotenv()
        # Establishing database connection
        self.connection = self.initialize_db()
        self.url = url_name
        logger.info("Initialized crawler.")
        self.motorcycles = self.get_motorcycles()
        if self.motorcycles:
            # Inserting motorcycles from the main page to the database by brand, model and years.
            self.insert_motorcycles_to_database()
            # Getting parts for motorcycles one by one.
            # self.parse_parts_for_motorcycles()
            # Closing database connection.
            if self.connection:
                self.connection.close()
        else:
            logger.error("Could not find motorcycles.")

    def get_motorcycles(self):
        # Open a page
        html = self.get_page(self.url)
        if html:
            # Create a beautifulsoup object
            page = BeautifulSoup(html, "html.parser")
            # Parse the page and return list of motorcycle objects.
            return self.parse_main_page(page)
        else:
            logger.error("Could not get HTML page.")

    def initialize_db(self):
        try:
            connection = psycopg2.connect(os.getenv("DATABASE_URL"))
            logger.info("Succesfully connected to the database.")
        except (Exception, psycopg2.Error) as error:
            print("Error while connecting to PostgreSQL:", error)
        return connection

    def parse_main_page(self, page):
        motorcycles = []
        # Finding all links in the page.
        links = page.find_all("a")
        filtered_links = [
            link for link in links if link.get("href") not in IGNORED_LINK_URLS
        ]
        for link in filtered_links:
            motorcycle = {}
            listing_text = " ".join(link.text.split())
            # Looping over motorcycle brands
            for brand in top_motorcycle_brands:
                # Checking if the brand is in the listing text.
                if brand.lower() in listing_text.lower():
                    motorcycle["brand"] = brand
                    # Removing the brand name from the listing text.
                    listing_without_brand = listing_text.replace(brand, "").replace(
                        "-&gt", ""
                    )
                    # Extracting the year information
                    if years := self.extract_year(listing_without_brand):
                        motorcycle["years"] = [years["start"]]
                        if years.get("end"):
                            motorcycle["years"].append(years["end"])
                        motorcycle["model"] = listing_without_brand[
                            : years["year_index"]
                        ].strip()
                        motorcycle["href"] = link.get("href")
            if all(key in motorcycle for key in ["brand", "years", "model"]):
                motorcycles.append(motorcycle)
                logger.info(motorcycle)
            else:
                logger.debug("Found invalid motorcycle.")
                logger.info(link)
        logger.info(f"{len(motorcycles)} motorcycles found in total.")
        return motorcycles

    def parse_parts_for_motorcycles(self):
        # Get all motorcycles by year from the database.
        with self.connection.cursor() as cursor:
            # Getting all individual motorcycles from the database.
            cursor.execute("SELECT * FROM Years;")
            response = cursor.fetchall()[0]
            # Iterating over the motorcycles one by one
            for moto_entry in response:
                # Getting link to the part page of the disassembled motorcycle
                moto_entry_url = moto_entry[3]
                logger.info("Getting part page", moto_entry_url)
                sleep(5)
                """if page := self.get_page(moto_entry_url):
                    # Create a beautifulsoup object
                    soup = BeautifulSoup(page, 'html.parser')
                    # Parse the page and return a list of parts.
                    return self.parse_part_page(soup)"""

    def get_page(self, page_url):
        try:
            # Send an HTTP GET request to the URL
            response = requests.get(page_url)
            if response.status_code == 200:
                return response.text
            else:
                logger.error(
                    "Failed to retrieve the web page. Status code:",
                    response.status_code,
                )
                return None
        except requests.exceptions.RequestException as e:
            logger.error("Error:", e)

    """ Parses motorcycle part html page and returns a list of parts. """

    def parse_part_page(self, page):
        filtered_tables = [
            table for table in page.find_all("table", {"align": False, "class": False})
        ]
        # Each part is one table
        for table in filtered_tables:
            part = {}
            table_rows = table.find_all("tr")
            # Finding images
            image_tags = table_rows[0].find_all("a")
            for image_tag in image_tags:
                image_link = image_tag.get("href")
                # Check if the href attribute starts with "/images"
                if image_link.startswith("images/"):
                    part["image_href"] = image_link

            # Finding part name

            first_col = table_rows[0].find_all("td")
            if len(first_col) == 3:
                part_name_cell = first_col[2]
                part["name"] = (
                    part_name_cell.text.strip()
                    if part_name_cell.text
                    else "Unnamed part"
                )

            # Part number
            second_col = table_rows[1].find_all("td")
            if len(second_col) == 2:
                part_number_cell = second_col[1]
                part["part_number"] = part_number_cell.text.strip()

            # Part description
            third_col = table_rows[2].find_all("td")
            if len(third_col) == 2:
                part_description_cell = third_col[1]
                part["description"] = part_description_cell.text.strip()

            # Part price
            fourth_col = table_rows[3].find_all("td")
            if len(second_col) == 2:
                part_price_cell = fourth_col[1]
                if part_price := part_price_cell.find("b"):
                    try:
                        part["price"] = int(part_price.text.strip("EUR"))
                    except ValueError:
                        return False

            logger.info(part)

    def check_if_brand_exists(self, brand_name, cursor):
        cursor.execute("SELECT * FROM Brands WHERE brand_name = %s", (brand_name,))
        if cursor.fetchone():
            return True
        else:
            return False

    def check_if_model_exists(self, brand_name, model_name, cursor):
        cursor.execute(
            "SELECT * FROM Models WHERE brand_name = %s AND model_name = %s",
            (
                brand_name,
                model_name,
            ),
        )
        if cursor.fetchone():
            return True
        else:
            return False

    def insert_motorcycles_to_database(self):
        print(f"Inserting to database {len(self.motorcycles)} motos.")

        try:
            with self.connection.cursor() as cursor:
                cursor.execute("SELECT brand_name FROM Brands;")
                existing_brands = [entry[0] for entry in cursor.fetchall()]
                for idx, motorcycle in enumerate(self.motorcycles):
                    print(
                        f"Processing motorcycle nr. {idx} and brand is {motorcycle.get('brand')}"
                    )

                    # If motorcycle brand is not in database already, we add it.
                    if motorcycle.get("brand") not in existing_brands:
                        print("Brand was not in database, adding it to database.")
                        cursor.execute(BRAND_INSERT_QUERY, (motorcycle.get("brand"),))
                        cursor.execute(
                            MODEL_INSERT_QUERY,
                            (motorcycle.get("model"), motorcycle.get("brand")),
                        )
                    else:
                        cursor.execute(
                            MODEL_INSERT_QUERY,
                            (motorcycle.get("model"), motorcycle.get("brand")),
                        )
                    self.connection.commit()

                    # Getting model id from database in order to add year entries
                    cursor.execute(
                        "SELECT model_id FROM Models WHERE model_name = %s AND brand_name = %s;",
                        (motorcycle.get("model"), motorcycle.get("brand")),
                    )

                    if model_id := cursor.fetchone():
                        years = motorcycle.get("years")
                        # If the years list has more than one element, then it is a year range instead of singular year.
                        if len(years) > 1:
                            # Looping over the range of years.
                            for year in range(years[0], years[1] + 1):
                                # Adding each year separately.
                                cursor.execute(
                                    YEAR_INSERT_QUERY,
                                    (model_id[0], year, motorcycle.get("href")),
                                )
                        else:
                            cursor.execute(
                                YEAR_INSERT_QUERY,
                                (model_id[0], years[0], motorcycle.get("href")),
                            )
                    self.connection.commit()
        except (Exception, psycopg2.Error) as error:
            print("Error while inserting data:", error)

    # Function to check if a year or year range is valid

    def is_valid_year(self, year_string):
        try:
            year_int = int(year_string.strip())
            return year_int >= min_valid_year and year_int <= current_year
        except ValueError:
            return False

    """
    Checks if the listing text contains a year range or a singular year
    Returns an array with either one or two elements (singular year or start+end years)
    """

    def extract_year(self, listing_text) -> dict:
        year_info = {}
        year = listing_text[-4:]
        # Trying to find a year range by searching for a hyphen.
        index_of_year_range = listing_text.rfind("-", 0)
        # Checking if hyphen was found, and that it is safe to search around the hyphen for year values.
        if index_of_year_range > 4 and len(listing_text) >= index_of_year_range + 5:
            # Getting the 4 closest chars to the left of the hyphen
            left_of_hyphen = listing_text[index_of_year_range - 4 : index_of_year_range]
            # Getting 4 closest chars to the right of the hyphen
            right_of_hyphen = listing_text[index_of_year_range + 1 :]
            # If both sides are valid, then year range is correct.
            if self.is_valid_year(left_of_hyphen) and self.is_valid_year(
                right_of_hyphen
            ):
                year_info["start"] = left_of_hyphen
                year_info["end"] = right_of_hyphen
                year_info["year_index"] = index_of_year_range - 4
                return year_info
            elif self.is_valid_year(year):
                year_info["start"] = year
                year_info["year_index"] = len(listing_text) - 4
        # If the last 4 characters of the listing text were a valid year, then choosing that as the year.
        elif self.is_valid_year(year):
            year_info["start"] = year
            year_info["year_index"] = len(listing_text) - 4

        return year_info


def main():
    print("Hiya world.")
    crawler = Crawler("https://www.purkuosat.net/lista.htm")


if __name__ == "__main__":
    main()
