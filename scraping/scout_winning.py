"""
sofascore_lpf_generales.py
──────────────────────────
Descarga las estadísticas GENERALES de todos los partidos de una jornada
de la Liga Profesional Argentina y las guarda en un Excel existente.
Ahora soporta Torneo, Temporada y Slug por consola para descargar Playoffs.

Dependencias:
    pip install playwright openpyxl
    playwright install chromium
"""

import argparse
import time
import sys
import os
import traceback
import json
from playwright.sync_api import sync_playwright

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

# ──────────────────────────────────────────────────────────────────
# CONFIGURACIÓN POR DEFECTO
# ──────────────────────────────────────────────────────────────────
TOURNAMENT_ID = 155
SEASON_ID     = 87913
SLUG_RONDA    = ""
BASE_URL      = "https://www.sofascore.com"
SLEEP_REQ     = 2.0

# ──────────────────────────────────────────────────────────────────
# ESTADÍSTICAS ORIGINALES (generales)
# ──────────────────────────────────────────────────────────────────
ESTADISTICAS_CLAVE = {
    "Ball possession":         "Posesión de balón",
    "Expected goals":          "Goles esperados (xG)",
    "Total shots":             "Tiros totales",
    "Shots on target":         "Tiros al arco",
    "Shots off target":        "Tiros afuera",
    "Blocked shots":           "Tiros bloqueados",
    "Corner kicks":            "Córners",
    "Offsides":                "Fueras de juego",
    "Fouls":                   "Faltas",
    "Yellow cards":            "Tarjetas amarillas",
    "Red cards":               "Tarjetas rojas",
    "Passes":                  "Pases totales",
    "Accurate passes":         "Pases precisos",
    "Accurate long balls":     "Balones largos precisos",
    "Accurate crosses":        "Centros precisos",
    "Goalkeeper saves":        "Atajadas del arquero",
    "Tackles":                 "Quites",
    "Interceptions":           "Intercepciones",
    "Clearances":              "Despejes",
    "Big chances":             "Ocasiones claras",
    "Big chances missed":      "Ocasiones claras falladas",
    "Big chances created":     "Ocasiones claras creadas",
    "Passes into final third": "Pases al último tercio",
    "Dribbles":                "Regates intentados",
    "Dribbles succeeded":      "Regates exitosos",
    "Passes accuracy":         "Precisión de pases (%)",
    "Shots inside box":        "Tiros dentro del área",
    "Shots outside box":       "Tiros fuera del área",
    "Expected goals on target":"xG al arco (xGOT)",
    "Goals prevented":         "Goles evitados (arquero)",
    "Duels won":               "Duelos ganados",
    "Aerial duels won":        "Duelos aéreos ganados",
    "Ball recoveries":         "Recuperaciones de balón",
    "Errors leading to shot":  "Errores que generaron tiro",
}

# Métricas de porcentaje que NO deben sumarse entre períodos
# (se recalculan desde los valores absolutos)
METRICAS_PORCENTAJE = {
    "Ball possession",
    "Passes accuracy",
}

# ──────────────────────────────────────────────────────────────────
# MÉTRICAS CALCULADAS
# ──────────────────────────────────────────────────────────────────
def calcular_metricas_derivadas(stats: dict) -> list:
    def n(key, equipo):
        try:
            v = stats.get(key, {}).get(equipo, "0")
            return float(str(v).replace('%', '').strip() or 0)
        except (ValueError, TypeError):
            return 0.0

    derivadas = []

    for eq, label in [("home", "Local"), ("away", "Visitante")]:
        tiros_tot   = n("Total shots", eq)
        tiros_arco  = n("Shots on target", eq)
        conversion  = round(tiros_arco / tiros_tot * 100, 1) if tiros_tot else 0.0
        derivadas.append([f"Precisión de tiros - {label} (%)", conversion, ""])

    for eq, label in [("home", "Local"), ("away", "Visitante")]:
        xg         = n("Expected goals", eq)
        tiros_tot  = n("Total shots", eq)
        xg_por_tiro = round(xg / tiros_tot, 3) if tiros_tot else 0.0
        derivadas.append([f"xG por tiro - {label}", xg_por_tiro, ""])

    for eq, label in [("home", "Local"), ("away", "Visitante")]:
        creadas  = n("Big chances created", eq)
        falladas = n("Big chances missed", eq)
        efic     = round((creadas - falladas) / creadas * 100, 1) if creadas else 0.0
        derivadas.append([f"Eficiencia oportunidades claras - {label} (%)", efic, ""])

    for eq, label in [("home", "Local"), ("away", "Visitante")]:
        intentados = n("Dribbles", eq)
        exitosos   = n("Dribbles succeeded", eq)
        ratio      = round(exitosos / intentados * 100, 1) if intentados else 0.0
        derivadas.append([f"% Regates exitosos - {label}", ratio, ""])

    total_duelos = n("Duels won", "home") + n("Duels won", "away")
    for eq, label in [("home", "Local"), ("away", "Visitante")]:
        ganados = n("Duels won", eq)
        ratio   = round(ganados / total_duelos * 100, 1) if total_duelos else 0.0
        derivadas.append([f"% Duelos ganados - {label}", ratio, ""])

    dif_xg = round(n("Expected goals", "home") - n("Expected goals", "away"), 2)
    derivadas.append(["Diferencial xG (Local - Visitante)", dif_xg, ""])

    for eq, label in [("home", "Local"), ("away", "Visitante")]:
        dentro = n("Shots inside box", eq)
        total  = n("Total shots", eq)
        ratio  = round(dentro / total * 100, 1) if total else 0.0
        derivadas.append([f"% Tiros dentro del área - {label}", ratio, ""])

    return derivadas


EXCEL_DEFAULT = "/home/sebi/Documents/futbol/lpf_pred/data/actual/clausura26.xlsx"

# ──────────────────────────────────────────────────────────────────
# SESIÓN TLS
# ──────────────────────────────────────────────────────────────────
PROFILE_DIR = os.path.join(os.path.expanduser("~"), ".scout_sofascore_profile")
PROBE_URL   = f"{BASE_URL}/api/v1/config/country-sport-priorities/country/AR"


class _Resp:
    def __init__(self, status: int, text: str):
        self.status_code = status
        self.text = text

    def json(self):
        return json.loads(self.text)


class BrowserSession:
    """Navegador real (Chromium). Las requests se hacen con fetch() desde dentro
    de la página de SofaScore, así llevan la sesión/cookies del navegador."""

    def __init__(self, headless: bool = False, cdp_url: str = ""):
        self._pw = sync_playwright().start()
        self._cdp = bool(cdp_url)

        if cdp_url:
            # Conectarse a TU Chrome ya abierto (el que pasó Cloudflare a mano)
            print(f"   Conectando a Chrome en {cdp_url} …")
            self.browser = self._pw.chromium.connect_over_cdp(cdp_url)
            self.ctx = self.browser.contexts[0]
            self.page = next(
                (pg for pg in self.ctx.pages if "sofascore.com" in pg.url
                 and "captcha" not in pg.url),
                None,
            )
            if self.page is None:
                self.page = self.ctx.new_page()
                self.page.goto(f"{BASE_URL}/es/", wait_until="domcontentloaded")
                self.page.wait_for_timeout(4000)
        else:
            kwargs = dict(
                user_data_dir=PROFILE_DIR,
                headless=headless,
                locale="es-AR",
                args=["--disable-blink-features=AutomationControlled"],
                ignore_default_args=["--enable-automation"],
            )
            try:
                self.ctx = self._pw.chromium.launch_persistent_context(channel="chrome", **kwargs)
                print("   Usando Google Chrome instalado.")
            except Exception:
                self.ctx = self._pw.chromium.launch_persistent_context(**kwargs)
                print("   Usando Chromium de Playwright.")
            self.page = self.ctx.pages[0] if self.ctx.pages else self.ctx.new_page()
            self.page.goto(f"{BASE_URL}/es/", wait_until="domcontentloaded")
            self.page.wait_for_timeout(5000)

        self._verificar_acceso()

    def _fetch(self, url: str) -> _Resp:
        res = self.page.evaluate(
            """async (u) => {
                const r = await fetch(u, {credentials: 'include',
                                          headers: {'accept': 'application/json'}});
                return {status: r.status, text: await r.text()};
            }""",
            url,
        )
        return _Resp(res["status"], res["text"])

    def _verificar_acceso(self):
        r = self._fetch(PROBE_URL)
        if r.status_code == 200:
            print("   ✓ Acceso a la API OK.")
            return
        print(f"   ⚠  La prueba de acceso dio HTTP {r.status_code}.")
        print("      Si ves un captcha/desafío en la ventana del navegador, resolvelo.")
        input("      Cuando la página de SofaScore cargue normal, apretá Enter acá… ")
        self.page.reload(wait_until="domcontentloaded")
        self.page.wait_for_timeout(3000)
        r = self._fetch(PROBE_URL)
        print("   ✓ Acceso OK." if r.status_code == 200 else f"   ✗ Sigue HTTP {r.status_code}.")

    def get(self, url: str) -> _Resp:
        return self._fetch(url)

    def close(self):
        try:
            if not self._cdp:      # si es TU Chrome, no lo cerramos
                self.ctx.close()
        finally:
            self._pw.stop()


def build_session(headless: bool = False, cdp_url: str = "") -> BrowserSession:
    return BrowserSession(headless=headless, cdp_url=cdp_url)

def safe_get(session, url: str) -> dict | None:
    for intento in range(3):
        try:
            resp = session.get(url)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 404:
                return None
            if resp.status_code == 403:
                espera = (intento + 1) * 8
                cuerpo = (resp.text or "")[:150].replace("\n", " ")
                print(f"    ⚠  HTTP 403 (bloqueado) {cuerpo} — reintentando en {espera}s…")
                time.sleep(espera)
                continue
            espera = (intento + 1) * 4
            cuerpo = (resp.text or "")[:150].replace("\n", " ")
            print(f"    ⚠  HTTP {resp.status_code} — {cuerpo} — reintentando en {espera}s…")
            time.sleep(espera)
        except Exception as e:
            print(f"    ⚠  Excepción: {e}")
            time.sleep(3)
    print(f"    ✗  Falló tras 3 intentos: {url}")
    return None

# ──────────────────────────────────────────────────────────────────
# EXTRACCIÓN DE DATOS
# ──────────────────────────────────────────────────────────────────
def get_events(session, round_number: int) -> list[dict]:
    if SLUG_RONDA:
        url = f"{BASE_URL}/api/v1/unique-tournament/{TOURNAMENT_ID}/season/{SEASON_ID}/events/round/{round_number}/slug/{SLUG_RONDA}"
    else:
        url = f"{BASE_URL}/api/v1/unique-tournament/{TOURNAMENT_ID}/season/{SEASON_ID}/events/round/{round_number}"
        
    print(f"     URL: {url}")
    data = safe_get(session, url)
    if data is None:
        print("     ✗ La API no respondió datos (bloqueo, 404 o URL/temporada inválida). "
              "Revisá los mensajes de arriba.")
    eventos = data.get("events", []) if data else []
    
    # Si la API devuelve los dos torneos juntos (más de 15 partidos), 
    # nos quedamos solo con la segunda mitad (del 16 al 30)
    if len(eventos) > 15:
        return eventos[15:]
        
    return eventos
def extraer_numero(valor) -> float:
    if isinstance(valor, str):
        valor = valor.replace('%', '')
    try:
        return float(valor)
    except (ValueError, TypeError):
        return 0.0


def _acumular_periodos(data: dict) -> dict:
    """
    Construye stats_temporales sumando los períodos 1ST + 2ND (y ET si existe).
    Para métricas de porcentaje (posesión, precisión pases) se promedia en lugar
    de sumar, para no obtener valores absurdos como 101%.
    Devuelve el mismo formato que el camino normal: {nombre: {home: str, away: str}}
    """
    PERIODOS_SUMAR = ('1ST', '2ND', 'ET')
    periodos = [p for p in data['statistics'] if p['period'] in PERIODOS_SUMAR]

    if not periodos:
        # Último recurso: usar el primer período disponible tal cual
        fallback = data['statistics'][0]
        print(f"     ⚠  Usando período fallback único: {fallback['period']}")
        acum = {}
        for grupo in fallback['groups']:
            for item in grupo['statisticsItems']:
                nombre = item.get('name', '')
                if nombre not in acum:
                    acum[nombre] = {'home': item.get('home', '0'), 'away': item.get('away', '0')}
        return acum

    # Acumular sumando
    acum   = {}   # {nombre: {home: float, away: float}}
    conteo = {}   # cuántos períodos aportaron cada métrica (para promediar %)

    for periodo in periodos:
        for grupo in periodo['groups']:
            for item in grupo['statisticsItems']:
                nombre = item.get('name', '')
                if nombre not in acum:
                    acum[nombre]   = {'home': 0.0, 'away': 0.0}
                    conteo[nombre] = 0
                try:
                    acum[nombre]['home'] += float(
                        str(item.get('home', '0')).replace('%', '').strip() or 0
                    )
                    acum[nombre]['away'] += float(
                        str(item.get('away', '0')).replace('%', '').strip() or 0
                    )
                    conteo[nombre] += 1
                except (ValueError, TypeError):
                    pass

    # Promediar las métricas de porcentaje
    resultado = {}
    for nombre, vals in acum.items():
        cnt = conteo[nombre] or 1
        if nombre in METRICAS_PORCENTAJE:
            h = round(vals['home'] / cnt, 1)
            a = round(vals['away'] / cnt, 1)
        else:
            h = vals['home']
            a = vals['away']
        resultado[nombre] = {'home': str(h), 'away': str(a)}

    return resultado


def get_stats_partido(session, event_id: int) -> tuple[list | None, dict]:
    data = safe_get(session, f"{BASE_URL}/api/v1/event/{event_id}/statistics")
    if not data:
        return None, {}

    stats_temporales = {}

    if 'statistics' in data and len(data['statistics']) > 0:

        # ── Intentar período ALL primero (fase regular) ───────────────────
        stats_all = next((p for p in data['statistics'] if p['period'] == 'ALL'), None)

        if stats_all:
            # Camino normal: existe el período consolidado
            for grupo in stats_all['groups']:
                for item in grupo['statisticsItems']:
                    nombre_original = item.get('name', '')
                    if nombre_original not in stats_temporales:
                        stats_temporales[nombre_original] = {
                            'home': item.get('home', '0'),
                            'away': item.get('away', '0')
                        }
        else:
            # ── Fallback: playoffs / tiempo extra / penales ───────────────
            periodos_disp = [p['period'] for p in data['statistics']]
            print(f"     ⚠  Sin período ALL. Períodos disponibles: {periodos_disp}")
            print(f"     →  Acumulando períodos 1ST + 2ND (+ ET si existe)…")
            stats_temporales = _acumular_periodos(data)

    # Construir lista de estadísticas en el orden definido
    estadisticas_partido = []
    for clave_ingles, nombre_espanol in ESTADISTICAS_CLAVE.items():
        if clave_ingles in stats_temporales:
            val_home = stats_temporales[clave_ingles]['home']
            val_away = stats_temporales[clave_ingles]['away']
            estadisticas_partido.append([nombre_espanol, val_home, val_away])

    # ── INYECCIÓN MANUAL: PENALES A FAVOR ─────────────────────────────────
    # Se agrega al final de las estadísticas extraídas para rellenar a mano
    if estadisticas_partido:
        estadisticas_partido.append(["Penales a favor", 0, 0])

    return (estadisticas_partido if estadisticas_partido else None), stats_temporales
# ──────────────────────────────────────────────────────────────────
# ESTILOS EXCEL
# ──────────────────────────────────────────────────────────────────
def _fill(hex_color):
    return PatternFill("solid", fgColor=hex_color)

def _font(bold=False, color="000000", size=11):
    return Font(name="Arial", bold=bold, color=color, size=size)

def _border():
    s = Side(style="thin", color="B0BEC5")
    return Border(left=s, right=s, top=s, bottom=s)

def _align(h="center", wrap=False):
    return Alignment(horizontal=h, vertical="center", wrap_text=wrap)

def style(cell, fill, fnt, align=None):
    cell.fill      = fill
    cell.font      = fnt
    cell.border    = _border()
    cell.alignment = align or _align()

F_TITULO   = _fill("0D2B45")
F_HEADER   = _fill("1A3A5C")
F_RESULT   = _fill("2E7D32")
F_EVEN     = _fill("EAF0F6")
F_ODD      = _fill("FFFFFF")
F_DERIVADA = _fill("FFF3CD")
F_DER_HEAD = _fill("E65100")

def write_match_table(ws, start_row: int,
                      home_name: str, away_name: str,
                      goles_local, goles_visitante,
                      estadisticas: list,
                      metricas_derivadas: list) -> int:
    r = start_row
    C = 1

    ws.merge_cells(start_row=r, start_column=C, end_row=r, end_column=C + 2)
    tc = ws.cell(row=r, column=C, value=f"  {home_name}  vs  {away_name}")
    style(tc, F_TITULO, _font(bold=True, color="FFFFFF", size=12))
    r += 1

    for i, label in enumerate(["Métrica", home_name, away_name]):
        c = ws.cell(row=r, column=C + i, value=label)
        style(c, F_HEADER, _font(bold=True, color="FFFFFF"), _align(wrap=True))
    r += 1

    for i, val in enumerate(["Resultado", goles_local, goles_visitante]):
        c = ws.cell(row=r, column=C + i, value=val)
        style(c, F_RESULT, _font(bold=True, color="FFFFFF"))
    r += 1

    for idx, (metrica, val_home, val_away) in enumerate(estadisticas):
        fill_row = F_EVEN if idx % 2 == 0 else F_ODD
        cm = ws.cell(row=r, column=C,     value=metrica)
        ch = ws.cell(row=r, column=C + 1, value=val_home)
        ca = ws.cell(row=r, column=C + 2, value=val_away)
        style(cm, fill_row, _font(), _align(h="left"))
        style(ch, fill_row, _font())
        style(ca, fill_row, _font())
        r += 1

    if metricas_derivadas:
        r += 1

        ws.merge_cells(start_row=r, start_column=C, end_row=r, end_column=C + 2)
        th = ws.cell(row=r, column=C, value="  📊 Métricas derivadas (para modelo predictivo)")
        style(th, F_DER_HEAD, _font(bold=True, color="FFFFFF", size=11))
        r += 1

        for i, label in enumerate(["Métrica calculada", home_name, away_name]):
            c = ws.cell(row=r, column=C + i, value=label)
            style(c, F_HEADER, _font(bold=True, color="FFFFFF"), _align(wrap=True))
        r += 1

        for idx, (metrica, val_home, val_away) in enumerate(metricas_derivadas):
            fill_row = F_DERIVADA if idx % 2 == 0 else F_ODD
            cm = ws.cell(row=r, column=C,     value=metrica)
            ch = ws.cell(row=r, column=C + 1, value=val_home if val_home != "" else "-")
            ca = ws.cell(row=r, column=C + 2, value=val_away if val_away != "" else "-")
            style(cm, fill_row, _font(), _align(h="left"))
            style(ch, fill_row, _font())
            style(ca, fill_row, _font())
            r += 1

    return r

def set_col_widths(ws):
    ws.column_dimensions["A"].width = 40
    ws.column_dimensions["B"].width = 24
    ws.column_dimensions["C"].width = 24
    for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
        ws.row_dimensions[row[0].row].height = 20

# ──────────────────────────────────────────────────────────────────
# PROCESAMIENTO POR JORNADA
# ──────────────────────────────────────────────────────────────────
def procesar_jornada(session, wb: Workbook, round_number: int) -> bool:
    sheet_name = f"Fecha {round_number}" if not SLUG_RONDA else f"Fecha {round_number} - {SLUG_RONDA}"
    sheet_name = sheet_name[:31]  # límite de Excel

    print(f"\n{'='*54}")
    texto_ronda = f"FECHA {round_number}" if not SLUG_RONDA else f"FECHA {round_number} ({SLUG_RONDA})"
    print(f"  {texto_ronda}")
    print(f"{'='*54}")

    events = get_events(session, round_number)
    if not events:
        print("  ⚠  No se encontraron partidos. No se modifica el Excel.")
        return False

    # Recién ahora, con datos en mano, reemplazamos la hoja
    if sheet_name in wb.sheetnames:
        del wb[sheet_name]
    ws = wb.create_sheet(title=sheet_name)

    print(f"  {len(events)} partido(s) encontrado(s).\n")
    current_row = 1

    for event in events:
        event_id        = event.get("id")
        home_name       = event.get("homeTeam", {}).get("name", "Local")
        away_name       = event.get("awayTeam", {}).get("name", "Visitante")
        goles_local     = event.get("homeScore", {}).get("current", 0) or 0
        goles_visitante = event.get("awayScore", {}).get("current", 0) or 0

        print(f"  ⚽ {home_name} {goles_local} - {goles_visitante} {away_name}  (id={event_id})")
        time.sleep(SLEEP_REQ)

        print("     Obteniendo estadísticas generales del partido...")
        estadisticas, stats_crudas = get_stats_partido(session, event_id)

        if not estadisticas:
            print("     → Sin estadísticas disponibles, se omite.\n")
            continue

        metricas_derivadas = calcular_metricas_derivadas(stats_crudas)

        next_row = write_match_table(
            ws, current_row,
            home_name, away_name,
            goles_local, goles_visitante,
            estadisticas,
            metricas_derivadas,
        )
        current_row = next_row + 2
        print(f"     ✓ Tabla escrita hasta fila {next_row - 1}\n")

    set_col_widths(ws)
    return True

# ──────────────────────────────────────────────────────────────────
# ENTRY POINT
# ──────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Scouting Generales – Liga Profesional Argentina (SofaScore)"
    )
    parser.add_argument(
        "--jornada", "-j",
        type=int, nargs="+", required=True,
        help="Número(s) de jornada. Ej: --jornada 5   o   --jornada 1 2 3",
    )
    parser.add_argument(
        "--excel", "-e",
        type=str, default=EXCEL_DEFAULT,
        help=f"Ruta al Excel existente (default: {EXCEL_DEFAULT})",
    )
    parser.add_argument(
        "--torneo", "-t",
        type=int, default=155,
        help="ID del torneo (default: 155 para LPF regular)",
    )
    parser.add_argument(
        "--temporada", "-s",
        type=int, default=87913,
        help="ID de la temporada (default: 87913)",
    )
    parser.add_argument(
        "--slug",
        type=str, default="",
        help="Slug de la ronda para playoffs (ej: round-of-16)",
    )
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Correr el navegador sin ventana (menos fiable contra el anti-bot).",
    )
    parser.add_argument(
        "--cdp",
        type=str, default="",
        help="URL de un Chrome abierto con --remote-debugging-port (ej: http://localhost:9222).",
    )
    args = parser.parse_args()

    global TOURNAMENT_ID, SEASON_ID, SLUG_RONDA
    TOURNAMENT_ID = args.torneo
    SEASON_ID     = args.temporada
    SLUG_RONDA    = args.slug

    ruta_excel = args.excel

    if os.path.exists(ruta_excel):
        print(f"📂 Abriendo Excel existente: {ruta_excel}")
        wb = load_workbook(ruta_excel)
    else:
        print(f"📄 Excel no encontrado — se creará uno nuevo: {ruta_excel}")
        wb = Workbook()
        wb.remove(wb.active)

    print("🌐 Abriendo navegador con SofaScore...")
    session = build_session(headless=args.headless, cdp_url=args.cdp)

    hubo_datos = False
    try:
        for i, jornada in enumerate(args.jornada):
            try:
                if procesar_jornada(session, wb, jornada):
                    hubo_datos = True
            except Exception:
                print(f"\n❌ Error procesando Fecha {jornada}:")
                traceback.print_exc()
            if i < len(args.jornada) - 1:
                time.sleep(SLEEP_REQ)
    finally:
        session.close()

    if not hubo_datos:
        print("\n⚠  No se obtuvieron datos. El Excel NO fue modificado.")
        sys.exit(1)

    wb.save(ruta_excel)
    print(f"\n✅ Excel guardado en: {ruta_excel}")
    print(f"   Hojas disponibles: {', '.join(wb.sheetnames)}")

if __name__ == "__main__":
    main()