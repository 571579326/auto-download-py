import pymysql

conn = pymysql.connect(host='127.0.0.1', port=3306, user='root', password='root', database='auto_download')
cur = conn.cursor()
cur.execute(
    "SELECT config_code, config_name, page_name, url, status, sort_no "
    "FROM ad_browser_page_config "
    "WHERE config_code='acg18' AND status='1'"
)
rows = cur.fetchall()
print(f'Found {len(rows)} rows for config_code=acg18:')
for row in rows:
    print(f'  config_code={row[0]}, config_name={row[1]}, page_name={row[2]}, url={row[3]}, status={row[4]}, sort_no={row[5]}')
conn.close()
