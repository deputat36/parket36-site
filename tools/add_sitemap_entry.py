from pathlib import Path
import argparse
import datetime as dt

SITE = 'https://parket36.ru'


def clean_path(value):
    value = value.strip()
    if value.startswith(SITE):
        value = value[len(SITE):]
    if not value.startswith('/'):
        value = '/' + value
    if not value.endswith('/'):
        value += '/'
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    parser.add_argument('--lastmod', default=dt.date.today().isoformat())
    parser.add_argument('--changefreq', default='yearly')
    parser.add_argument('--priority', default='0.72')
    parser.add_argument('--file', default='sitemap.xml')
    args = parser.parse_args()

    path = clean_path(args.path)
    loc = SITE + path
    sitemap = Path(args.file)
    text = sitemap.read_text(encoding='utf-8')

    if f'<loc>{loc}</loc>' in text:
        print('Already exists: ' + loc)
        return

    entry = f'  <url><loc>{loc}</loc><lastmod>{args.lastmod}</lastmod><changefreq>{args.changefreq}</changefreq><priority>{args.priority}</priority></url>'
    text = text.replace('\n</urlset>', '\n' + entry + '\n</urlset>', 1)
    sitemap.write_text(text, encoding='utf-8')
    print('Added: ' + loc)


if __name__ == '__main__':
    main()
