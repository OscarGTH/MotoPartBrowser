IGNORED_LINK_URLS = [
"https://purkuosat.net/tilausohje.htm",
"https://purkuosat.net/lista.htm",
"https://purkuosat.net/kelkkalista.htm",
"https://purkuosat.net/uudetosat.htm",
"https://purkuosat.net/renkaat.htm",
"https://purkuosat.net/oljyt.htm",
"https://purkuosat.net/ostolomake.htm",
"https://purkuosat.net/myyntiehdot.htm",
"https://purkuosat.net/faq/faq.htm",
"https://purkuosat.net/yhteys.htm",
"https://purkuosat.net/yritys.htm",
"https://purkuosat.net/yoshimura.htm",
"https://purkuosat.net/puig.htm",
"http://www.purkuosat.net/",
"https://purkuosat.net/index.htm",
"https://purkuosat.net/mopolista.htm"]

top_motorcycle_brands = [
    "Honda",
    "Yamaha",
    "Kawasaki",
    "Can Am",
    "Can-Am",
    "Daelim",
    "Derbi",
    "Suzuki",
    "Harley-Davidson",
    "Harley Davidson",
    "GasGas",
    "YCF",
    "TM",
    "Husaberg",
    "KTM",
    "BMW",
    "Triumph",
    "Aprilia",
    "Moto Guzzi",
    "Indian Motorcycle",
    "Victory",
    "Buell",
    "Ducati",
    "Kymco",
    "MV Agusta",
    "Husqvarna",
    "Royal Enfield",
    "Bajaj",
    "Benelli",
    "Hyosung",
    "Zero Motorcycles",
    "Gilera",
    "Cagiva",
    "Norton",
    "Piaggio",
    "Vespa",
    "Ural"
]


BRAND_INSERT_QUERY = """
        INSERT INTO Brands (brand_name)
        VALUES (%s)
        ON CONFLICT (brand_name) DO NOTHING;
        """

MODEL_INSERT_QUERY = """
        INSERT INTO Models (model_id, model_name, brand_name)
        VALUES (uuid_generate_v4(), %s, %s)
        ON CONFLICT ON CONSTRAINT unique_model DO NOTHING;
        """

YEAR_INSERT_QUERY = """
        INSERT INTO Years (year_id, model_id, year_value, link_href)
        VALUES (uuid_generate_v4(), %s, %s, %s)
        ON CONFLICT ON CONSTRAINT unique_year_and_model DO NOTHING;
        """