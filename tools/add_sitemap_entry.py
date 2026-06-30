from pathlib import Path
import argparse
import datetime as dt

SITE = 'https://parket36.ru'
CLOSING_TAG = '\n</urlset>'


def clean_path(value):
    value = value.strip()
    if not value:
        raise SystemExit('Path is required')
    if value.startswith(SITE):
        value = value[len(SITE):]
    if not value.startswith('/'):
        value = '/' + value
    if not value.endswith('/'):
        value += '/'
    return value


def valid_date(value):
    try:
        dt.date.fromisoformat(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError('Use YYYY-MM-DD for --lastmod') from exc
    return value


def main():
    parser = argparse.ArgumentParser(description='Add one URL to sitemap.xml')
    parser.add_argument('path')
    parser.add_argument('--lastmod', default=dt.date.today().isoformat(), type=valid_date)
    parser.add_argument('--changefreq', default='yearly')
    parser.add_argument('--priority', default='0.72')
    parser.add_argument('--file', default='sitemap.xml')
    args = parser.parse_args()

    path = clean_path(args.path)
    loc = SITE + path
    sitemap = Path(args.file)
    text = sitemap.read_text(encoding='utf-8')

    if CLOSING_TAG not in text:
        raise SystemExit('Cannot find closing </urlset> marker')

    if f'<loc>{loc}</loc>' in text:
        print('Already exists: ' + loc)
        return

    entry = f'  <url><loc>{loc}</loc><lastmod>{args.lastmod}</lastmod><changefreq>{args.changefreq}</changefreq><priority>{args.priority}</priority></url>'
    text = text.replace(CLOSING_TAG, '\n' + entry + CLOSING_TAG, 1)
    sitemap.write_text(text, encoding='utf-8')
    print('Added: ' + loc)


if __name__ == '__main__':
    main()
