"""Hong Kong alerts the browser cannot read itself (no CORS), republished every 15 minutes for WorldViews:
  live/aqhi.json   EPD's current AQHI for the 18 monitoring stations (aqhi.gov.hk RSS), each placed at its station from the
                   CSDI "Air Quality Monitoring Network of Hong Kong" layer: GeoJSON, one point per station
  live/press.json  the Government's latest press releases (info.gov.hk RSS, newest 100): title, link, time; no body text
Both overwritten in place; no history kept yet. A source that fails keeps its last file (the run warns, exit 0).
Needs HF_TOKEN. `python3 live.py test` writes to ./data/ and uploads nothing."""
import datetime, email.utils, json, os, re, sys, urllib.request
import xml.etree.ElementTree as ET

REPO = 'alreadyopen/hk-alerts'
UA = {'User-Agent': 'AlreadyOpen hk-alerts (https://github.com/AlreadyOpen/hk-alerts)'}
AQHI = 'https://www.aqhi.gov.hk/epd/ddata/html/out/aqhi_ind_rss_Eng.xml'
STATIONS = ('https://portal.csdi.gov.hk/server/rest/services/common/epd_rcd_1629267205214_40635/FeatureServer/0/query'
            '?where=1%3D1&outFields=*&outSR=4326&f=geojson')   # all fields: EPD renames them 14-16 Oct 2026 (NAME_EN -> NameEN)
PRESS = 'https://www.info.gov.hk/gia/rss/general_en.xml'


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=60) as r:
        return r.read()


def aqhi():
    """'Central/Western - General Stations: 5 Moderate - Wed, 14 Oct 2026 08:30' per item, joined to the CSDI station by name"""
    at = {}
    for f in json.loads(get(STATIONS))['features']:
        p = f['properties']
        name = p.get('NameEN') or p.get('NAME_EN') or p.get('FacilityName') or ''   # new name, old name, the AQHI layer's name
        at[re.sub(r'\s+Air Quality Monitoring Station$', '', name).strip().lower()] = f
    out, missing = [], []
    for it in ET.fromstring(get(AQHI)).iter('item'):
        name, desc = it.findtext('title', '').strip(), it.findtext('description', '').strip()
        m = re.match(r'(.+?) - (General|Roadside) Stations?: (\d+\+?) (.+?) - (.+)$', desc)
        f = at.get(name.lower())
        if not m or not f:
            missing.append(name); continue
        t = datetime.datetime.strptime(m[5].strip(), '%a, %d %b %Y %H:%M').replace(tzinfo=datetime.timezone(datetime.timedelta(hours=8)))
        out.append({'type': 'Feature', 'geometry': f['geometry'], 'properties': {
            'station': name, 'kind': m[2].lower(), 'aqhi': int(m[3].rstrip('+')), 'aqhi_text': m[3], 'risk': m[4], 'time': t.isoformat(),
            'link': it.findtext('link', '')}})
    assert out, 'no AQHI station parsed'
    if missing:
        print(f'::warning::AQHI: no position or no reading for {missing}')
    return {'type': 'FeatureCollection', 'source': 'Environmental Protection Department (AQHI), positions from CSDI', 'features': out}


def press():
    items = []
    for it in ET.fromstring(get(PRESS)).iter('item'):
        when = email.utils.parsedate_to_datetime(it.findtext('pubDate', ''))
        items.append({'title': it.findtext('title', '').strip(), 'link': it.findtext('link', '').strip(), 'time': when.isoformat()})
    assert items, 'no press release parsed'
    return {'source': 'Information Services Department, Government press releases', 'items': items}


def main():
    test = sys.argv[1:] == ['test']
    out_dir = 'data' if test else '/tmp/hk-alerts'
    os.makedirs(out_dir, exist_ok=True)
    now = datetime.datetime.now(datetime.UTC).isoformat(timespec='seconds')
    files, report = [], {'run': now}
    for name, make in (('aqhi', aqhi), ('press', press)):
        try:
            d = make()
        except Exception as e:                                   # one source down: keep its last file, still publish the other
            print(f'::warning::{name}: {e}; keeping the last file'); report[name] = 'failed'; continue
        d['fetched'] = now
        path = os.path.join(out_dir, f'{name}.json')
        json.dump(d, open(path, 'w'), ensure_ascii=False, separators=(',', ':'))
        files.append((path, f'live/{name}.json'))
        report[name] = len(d.get('features') or d.get('items'))
    if files and not test:
        from huggingface_hub import batch_bucket_files, create_bucket
        create_bucket(REPO, private=False, exist_ok=True)
        batch_bucket_files(REPO, add=files)
    print(json.dumps(report))


if __name__ == '__main__':
    main()
