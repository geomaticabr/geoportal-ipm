"""Gera dados/municipios.json e dados/limites.json a partir do CSV e dos pmtiles."""
import pandas as pd, json, math, gzip
from pmtiles.reader import Reader, MmapSource
import mapbox_vector_tile as mvt

d = pd.read_csv('dados/IPMporSexoeRaca.csv', sep=';', decimal=',')
S = ['qtd_pes_pobres','qtd_pes_vulneraveis','qtd_pes_pob_vul','qtd_0a11_pobres','qtd_0a11_vulneraveis','qtd_0a11_pob_vul','qtd_pessoas','qtd_0a11']
C = ['nom_mun','cod_regiao','cod_uf','IPM','IPM_quintis','num_idhm','num_ivs','num_ibeu','num_renda']
g = d.groupby('cod_mun')
const = g[C].first()          # campos constantes por município: não são somados
sums = g[S].sum()             # campos quantitativos: somados entre sexo/raça
sx = d.pivot_table(index='cod_mun', columns='sxraca', values='qtd_pessoas', aggfunc='sum', fill_value=0).reindex(columns=range(1, 8), fill_value=0)
out = {}
for m in const.index:
    r = const.loc[m]
    out[str(m)] = dict(n=r.nom_mun, r=int(r.cod_regiao), u=int(r.cod_uf), ipm=round(float(r.IPM), 2), q=int(r.IPM_quintis),
        idhm=float(r.num_idhm), ivs=float(r.num_ivs), ibeu=float(r.num_ibeu), renda=round(float(r.num_renda), 2),
        s={k: round(float(sums.loc[m, k]), 1) for k in S}, sx=[round(float(x), 1) for x in sx.loc[m]])
# bbox de cada município (união dos pedaços nos tiles z5) para zoom na busca por nome
def tile_bboxes(f, layer, z=5):
    r = Reader(MmapSource(open(f, 'rb')))
    n = 2 ** z; res = {}
    for x in range(n):
        for y in range(n):
            raw = r.get(z, x, y)
            if not raw: continue
            try: raw = gzip.decompress(raw)
            except Exception: pass
            lay = mvt.decode(raw, default_options={'y_coord_down': False})[layer]
            ext = lay.get('extent', 4096)
            for ft in lay['features']:
                geo = ft['geometry']
                polys = geo['coordinates'] if geo['type'] == 'MultiPolygon' else [geo['coordinates']]
                pts = [p for poly in polys for ring in poly for p in ring]
                xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
                lon = lambda px: (x + px / ext) / n * 360 - 180
                lat = lambda py: math.degrees(math.atan(math.sinh(math.pi * (1 - 2 * (y + 1 - py / ext) / n))))
                b = [lon(min(xs)), lat(min(ys)), lon(max(xs)), lat(max(ys))]
                k = ft['properties']['CD_MUN']; o = res.get(k)
                res[k] = b if not o else [min(o[0], b[0]), min(o[1], b[1]), max(o[2], b[2]), max(o[3], b[3])]
    return res
MB = tile_bboxes('base/BR_Municipios_2025 10 por cento mapshifter.pmtiles', 'BR_Municipios_2025 10 por cento')
for k in out:
    if k in MB: out[k]['b'] = [round(v, 3) for v in MB[k]]
json.dump(out, open('dados/municipios.json', 'w', encoding='utf-8'), separators=(',', ':'), ensure_ascii=False)

def tile0(f, layer):
    r = Reader(MmapSource(open(f, 'rb')))
    raw = r.get(0, 0, 0)
    try: raw = gzip.decompress(raw)
    except Exception: pass
    return mvt.decode(raw, default_options={'y_coord_down': False})[layer]['features']

def bbox(feat):
    ext = 4096
    lon = lambda x: x / ext * 360 - 180
    lat = lambda y: math.degrees(math.atan(math.sinh(math.pi * (2 * y / ext - 1))))
    geo = feat['geometry']
    polys = geo['coordinates'] if geo['type'] == 'MultiPolygon' else [geo['coordinates']]
    best = None
    for poly in polys:   # usa só o maior polígono (ignora ilhas oceânicas)
        pts = [pt for ring in poly for pt in ring]
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
        b = (min(xs), min(ys), max(xs), max(ys))
        if best is None or (b[2]-b[0])*(b[3]-b[1]) > (best[2]-best[0])*(best[3]-best[1]): best = b
    return [round(lon(best[0]), 3), round(lat(best[1]), 3), round(lon(best[2]), 3), round(lat(best[3]), 3)]
lim = {'ufs': {}, 'regioes': {}}
for ft in tile0('base/BR_UF_geodataviewer.pmtiles', 'uf_simplificado'):
    p = ft['properties']; lim['ufs'][p['CD_UF']] = dict(nome=p['NM_UF'], sigla=p['SIGLA_UF'], regiao=p['CD_REGIAO'], bbox=bbox(ft))
for ft in tile0('base/BR_Regioes_2025_geodataviewer.pmtiles', 'GR_simplificado'):
    p = ft['properties']; lim['regioes'][p['CD_REGIAO']] = dict(nome=p['NM_REGIAO'], sigla=p['SIGLA_RG'], bbox=bbox(ft))
json.dump(lim, open('dados/limites.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(len(out), lim)



