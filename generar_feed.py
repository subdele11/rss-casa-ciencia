#!/usr/bin/env python3
"""Requiere Python 3.9+ y lxml (python3 -m pip install lxml)."""
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from email.utils import format_datetime
from urllib.parse import urljoin
from zoneinfo import ZoneInfo
import xml.etree.ElementTree as ET
from lxml import html

URL = 'https://www.casadelaciencia.csic.es/es/noticias'

def generate(source):
    doc = html.fromstring(source)
    rows = doc.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," view-noticias ")]//div[contains(concat(" ",normalize-space(@class)," ")," views-row ")]')
    rss = ET.Element('rss', version='2.0')
    ch = ET.SubElement(rss, 'channel')
    for tag, value in [('title','Casa de la Ciencia de Sevilla · Noticias'),('link',URL),('description','Noticias de la Casa de la Ciencia del CSIC en Sevilla. Feed generado a partir de su página pública.'),('language','es-ES'),('lastBuildDate',format_datetime(datetime.now(timezone.utc))),('ttl','360')]:
        ET.SubElement(ch,tag).text = value
    seen = set()
    for row in rows:
        links = row.xpath('.//div[contains(concat(" ",normalize-space(@class)," ")," views-field-title ")]//a')
        dates = row.xpath('.//div[contains(concat(" ",normalize-space(@class)," ")," views-field-created ")]')
        if not links or not dates:
            raise ValueError('Estructura inesperada: falta título o fecha')
        a = links[0]
        link = urljoin(URL,a.get('href'))
        if link in seen: continue
        seen.add(link)
        date = datetime.strptime(dates[0].text_content().strip(),'%d/%m/%Y').replace(tzinfo=ZoneInfo('Europe/Madrid'))
        item = ET.SubElement(ch,'item')
        ET.SubElement(item,'title').text = ' '.join(a.text_content().split())
        ET.SubElement(item,'link').text = link
        ET.SubElement(item,'guid',isPermaLink='true').text = link
        # La fuente solo publica el día: se utiliza medianoche local.
        ET.SubElement(item,'pubDate').text = format_datetime(date)
    if not seen: raise ValueError('No se encontraron noticias; se conserva el RSS anterior')
    ET.indent(rss)
    return ET.tostring(rss,encoding='utf-8',xml_declaration=True), len(seen)

if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--html',type=Path,help='HTML local para verificar sin descargar')
    p.add_argument('--output',type=Path,default=Path(__file__).with_name('casa_ciencia.xml'))
    args = p.parse_args()
    if args.html:
        source = args.html.read_bytes()
    else:
        source = subprocess.run(['curl','--http1.1','--fail','--location','--retry','3','--max-time','60','--silent','--show-error',URL],capture_output=True,check=True).stdout
        if b'</html>' not in source.lower(): raise ValueError('Descarga incompleta')
    data,count = generate(source)
    tmp = args.output.with_suffix('.tmp')
    tmp.write_bytes(data)
    ET.parse(tmp)
    tmp.replace(args.output)
    print(f'{count} noticias: {args.output}')
