from flask import Flask, render_template_string, request
import requests
from bs4 import BeautifulSoup
import random
import psycopg2
from psycopg2 import sql

app = Flask(__name__)

USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Firefox/53.0',
    'Mozilla/5.0 (Windows NT 10.0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.112 Safari/537.3',
    'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.3',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_12_2) AppleWebKit/602.3.12 (KHTML, like Gecko) Version/10.0.2 Safari/602.3.12'
]

DATABASE = {
    'dbname': 'scraper',
    'user': 'Mark',
    'password': 'Makfam2024',
    'host': 'localhost',
    'port': '5432'
}

def get_db_connection():
    return psycopg2.connect(**DATABASE)

def sanitize_identifier(name):
    """Sanitize and replace special characters for SQL identifiers."""
    return name.replace(" ", "_").replace("'", "").replace('"', "").replace("(", "").replace(")", "").lower()

def create_table_if_not_exists(table_name, headers):
    sanitized_headers = [sanitize_identifier(header) for header in headers]
    columns = ', '.join([f"{header} TEXT" for header in sanitized_headers])
    create_table_query = sql.SQL("""
        CREATE TABLE IF NOT EXISTS public.{table_name} (
            id SERIAL PRIMARY KEY,
            {columns},
            url TEXT
        )
    """).format(
        table_name=sql.Identifier(table_name),
        columns=sql.SQL(columns)
    )
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(create_table_query)
    except Exception as e:
        print(f"An error occurred while creating the table: {e}")

def save_data_to_db(table_name, headers, data_rows, url):
    sanitized_headers = [sanitize_identifier(header) for header in headers]
    insert_query = sql.SQL("""
        INSERT INTO public.{table_name} ({fields})
        VALUES ({values})
    """).format(
        table_name=sql.Identifier(table_name),
        fields=sql.SQL(', ').join(map(sql.Identifier, sanitized_headers + ['url'])),
        values=sql.SQL(', ').join(sql.Placeholder() * (len(sanitized_headers) + 1))
    )
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                for data in data_rows:
                    if len(data) == len(sanitized_headers):  # Ensure data matches headers
                        cursor.execute(insert_query, data + [url])
                    else:
                        print(f"Data row does not match headers: {data}")
    except Exception as e:
        print(f"An error occurred while saving data: {e}")

def extract_info(soup, url):
    try:
        tables = soup.find_all('table')
        html_tables = []  # To store HTML tables
        for idx, table in enumerate(tables):
            headers = [th.text.strip() for th in table.find('tr').find_all(['th', 'td'])]
            if not headers:
                continue

            table_name = f"rfps_table_{idx + 1}"
            create_table_if_not_exists(table_name, headers)

            rows = table.find_all('tr')[1:]  # Skip the header row
            data_rows = [
                [col.text.strip() for col in row.find_all(['td', 'th'])]
                for row in rows if len(row.find_all(['td', 'th'])) == len(headers)
            ]

            if data_rows:
                save_data_to_db(table_name, headers, data_rows, url)

            # Create HTML table
            html_table = "<table border='1'><thead><tr>{}</tr></thead><tbody>{}</tbody></table>".format(
                ''.join([f"<th>{header}</th>" for header in headers]),
                ''.join([
                    "<tr>{}</tr>".format(''.join([f"<td>{data}</td>" for data in row]))
                    for row in data_rows
                ])
            )
            html_tables.append(html_table)

        return "<p>Data extraction and saving complete.</p>" + ''.join(html_tables)
    except Exception as e:
        return f"An error occurred while extracting information: {e}"

def get_page_content(url):
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return response.content
    except requests.exceptions.RequestException as e:
        return f"An error occurred: {e}"

def parse_html(content):
    try:
        return BeautifulSoup(content, 'html.parser')
    except Exception as e:
        return f"An error occurred while parsing HTML: {e}"

@app.route('/')
def home():
    url = request.args.get('url')
    if not url:
        return render_template_string("""
        <h1>Web Scraping Tool</h1>
        <form method="get">
            <label for="url">Enter URL:</label>
            <input type="text" id="url" name="url" placeholder="Enter URL here">
            <input type="submit" value="Scrape">
        </form>
        """)

    content = get_page_content(url)
    if isinstance(content, str) and content.startswith('Error'):
        return content

    soup = parse_html(content)
    if isinstance(soup, str) and soup.startswith('An error occurred'):
        return soup

    table_data = extract_info(soup, url)
    return render_template_string("""
    <h1>Web Scraping Result</h1>
    <form method="get">
        <label for="url">Enter URL:</label>
        <input type="text" id="url" name="url" value="{{ url }}">
        <input type="submit" value="Scrape">
    </form>
    <div>{{ table_data|safe }}</div>
    """, url=url, table_data=table_data)

if __name__ == "__main__":
    app.run(debug=True)
