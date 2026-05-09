"""
Dicionário local de cidades → aeroportos (código IATA + nome).
Permite busca por nome de cidade sem precisar de API externa.
"""
from __future__ import annotations

import unicodedata
from typing import Dict, List, Tuple

# city_key (minúsculo sem acento) → lista de (IATA, nome legível)
AIRPORTS: Dict[str, List[Tuple[str, str]]] = {
    # ──────────────── Brasil ────────────────
    "sao paulo":        [("GRU", "São Paulo - Guarulhos"), ("CGH", "São Paulo - Congonhas")],
    "guarulhos":        [("GRU", "São Paulo - Guarulhos")],
    "congonhas":        [("CGH", "São Paulo - Congonhas")],
    "campinas":         [("VCP", "Campinas - Viracopos")],
    "rio de janeiro":   [("GIG", "Rio de Janeiro - Galeão"), ("SDU", "Rio - Santos Dumont")],
    "rio":              [("GIG", "Rio de Janeiro - Galeão"), ("SDU", "Rio - Santos Dumont")],
    "galeao":           [("GIG", "Rio de Janeiro - Galeão")],
    "santos dumont":    [("SDU", "Rio - Santos Dumont")],
    "brasilia":         [("BSB", "Brasília")],
    "salvador":         [("SSA", "Salvador")],
    "recife":           [("REC", "Recife")],
    "fortaleza":        [("FOR", "Fortaleza")],
    "belem":            [("BEL", "Belém")],
    "manaus":           [("MAO", "Manaus")],
    "porto alegre":     [("POA", "Porto Alegre")],
    "curitiba":         [("CWB", "Curitiba")],
    "belo horizonte":   [("CNF", "BH - Confins"), ("PLU", "BH - Pampulha")],
    "confins":          [("CNF", "BH - Confins")],
    "florianopolis":    [("FLN", "Florianópolis")],
    "maceio":           [("MCZ", "Maceió")],
    "natal":            [("NAT", "Natal")],
    "goiania":          [("GYN", "Goiânia")],
    "vitoria":          [("VIX", "Vitória")],
    "campo grande":     [("CGR", "Campo Grande")],
    "cuiaba":           [("CGB", "Cuiabá")],
    "porto velho":      [("PVH", "Porto Velho")],
    "sao luis":         [("SLZ", "São Luís")],
    "teresina":         [("THE", "Teresina")],
    "aracaju":          [("AJU", "Aracaju")],
    "macapa":           [("MCP", "Macapá")],
    "boa vista":        [("BVB", "Boa Vista")],
    "palmas":           [("PMW", "Palmas")],
    "rio branco":       [("RBR", "Rio Branco")],
    "joao pessoa":      [("JPA", "João Pessoa")],
    "foz do iguacu":    [("IGU", "Foz do Iguaçu")],
    "uberlandia":       [("UDI", "Uberlândia")],
    "londrina":         [("LDB", "Londrina")],
    "maringa":          [("MGF", "Maringá")],
    "ilheus":           [("IOS", "Ilhéus")],
    "porto seguro":     [("BPS", "Porto Seguro")],
    # ──────────────── América do Norte ────────────────
    "miami":            [("MIA", "Miami")],
    "nova york":        [("JFK", "Nova York - JFK"), ("EWR", "Newark"), ("LGA", "LaGuardia")],
    "new york":         [("JFK", "Nova York - JFK"), ("EWR", "Newark")],
    "orlando":          [("MCO", "Orlando")],
    "los angeles":      [("LAX", "Los Angeles")],
    "chicago":          [("ORD", "Chicago - O'Hare"), ("MDW", "Chicago Midway")],
    "boston":           [("BOS", "Boston")],
    "atlanta":          [("ATL", "Atlanta")],
    "dallas":           [("DFW", "Dallas - Fort Worth")],
    "houston":          [("IAH", "Houston")],
    "las vegas":        [("LAS", "Las Vegas")],
    "san francisco":    [("SFO", "San Francisco")],
    "seattle":          [("SEA", "Seattle")],
    "washington":       [("IAD", "Washington Dulles"), ("DCA", "Washington Reagan")],
    "toronto":          [("YYZ", "Toronto")],
    "vancouver":        [("YVR", "Vancouver")],
    "montreal":         [("YUL", "Montreal")],
    "cidade do mexico": [("MEX", "Cidade do México")],
    "cancun":           [("CUN", "Cancún")],
    "havana":           [("HAV", "Havana")],
    # ──────────────── América do Sul ────────────────
    "buenos aires":     [("EZE", "Buenos Aires - Ezeiza"), ("AEP", "Buenos Aires - Aeroparque")],
    "santiago":         [("SCL", "Santiago")],
    "lima":             [("LIM", "Lima")],
    "bogota":           [("BOG", "Bogotá")],
    "cartagena":        [("CTG", "Cartagena")],
    "medellin":         [("MDE", "Medellín")],
    "caracas":          [("CCS", "Caracas")],
    "quito":            [("UIO", "Quito")],
    "guayaquil":        [("GYE", "Guayaquil")],
    "montevideo":       [("MVD", "Montevidéu")],
    "asuncion":         [("ASU", "Assunção")],
    "santa cruz":       [("VVI", "Santa Cruz de la Sierra")],
    # ──────────────── Europa ────────────────
    "paris":            [("CDG", "Paris - Charles de Gaulle"), ("ORY", "Paris - Orly")],
    "londres":          [("LHR", "Londres - Heathrow"), ("LGW", "Londres - Gatwick")],
    "london":           [("LHR", "Londres - Heathrow")],
    "frankfurt":        [("FRA", "Frankfurt")],
    "amsterdam":        [("AMS", "Amsterdam")],
    "madri":            [("MAD", "Madri")],
    "madrid":           [("MAD", "Madri")],
    "barcelona":        [("BCN", "Barcelona")],
    "lisboa":           [("LIS", "Lisboa")],
    "lisbon":           [("LIS", "Lisboa")],
    "porto":            [("OPO", "Porto")],
    "roma":             [("FCO", "Roma - Fiumicino")],
    "rome":             [("FCO", "Roma - Fiumicino")],
    "milao":            [("MXP", "Milão - Malpensa")],
    "milan":            [("MXP", "Milão - Malpensa")],
    "zurique":          [("ZRH", "Zurique")],
    "zurich":           [("ZRH", "Zurique")],
    "viena":            [("VIE", "Viena")],
    "vienna":           [("VIE", "Viena")],
    "bruxelas":         [("BRU", "Bruxelas")],
    "brussels":         [("BRU", "Bruxelas")],
    "dublin":           [("DUB", "Dublin")],
    "estocolmo":        [("ARN", "Estocolmo")],
    "copenhagen":       [("CPH", "Copenhague")],
    "oslo":             [("OSL", "Oslo")],
    "helsinki":         [("HEL", "Helsinki")],
    "varsovia":         [("WAW", "Varsóvia")],
    "praga":            [("PRG", "Praga")],
    "budapest":         [("BUD", "Budapeste")],
    "atenas":           [("ATH", "Atenas")],
    "athens":           [("ATH", "Atenas")],
    "istanbul":         [("IST", "Istambul")],
    "istambul":         [("IST", "Istambul")],
    # ──────────────── Ásia / Oriente Médio / África ────────────────
    "dubai":            [("DXB", "Dubai")],
    "abu dhabi":        [("AUH", "Abu Dhabi")],
    "doha":             [("DOH", "Doha")],
    "toquio":           [("NRT", "Tóquio - Narita"), ("HND", "Tóquio - Haneda")],
    "tokyo":            [("NRT", "Tóquio - Narita"), ("HND", "Tóquio - Haneda")],
    "pequim":           [("PEK", "Pequim")],
    "beijing":          [("PEK", "Pequim")],
    "xangai":           [("PVG", "Xangai - Pudong")],
    "shanghai":         [("PVG", "Xangai - Pudong")],
    "hong kong":        [("HKG", "Hong Kong")],
    "seoul":            [("ICN", "Seul")],
    "seul":             [("ICN", "Seul")],
    "bangkok":          [("BKK", "Bangkok")],
    "cingapura":        [("SIN", "Cingapura")],
    "singapore":        [("SIN", "Cingapura")],
    "bali":             [("DPS", "Bali - Denpasar")],
    "mumbai":           [("BOM", "Mumbai")],
    "nova delhi":       [("DEL", "Nova Delhi")],
    "new delhi":        [("DEL", "Nova Delhi")],
    "joanesburgo":      [("JNB", "Joanesburgo")],
    "johannesburg":     [("JNB", "Joanesburgo")],
    "cairo":            [("CAI", "Cairo")],
    "nairobi":          [("NBO", "Nairóbi")],
    # ──────────────── Oceania ────────────────
    "sydney":           [("SYD", "Sydney")],
    "melbourne":        [("MEL", "Melbourne")],
    "brisbane":         [("BNE", "Brisbane")],
    "auckland":         [("AKL", "Auckland")],
}


# ── Países → principais aeroportos ──────────────────────────────────────────
# Cada país lista os aeroportos mais importantes (máx. 4) para não sobrecarregar
COUNTRIES: Dict[str, List[Tuple[str, str]]] = {
    "brasil":           [("GRU", "São Paulo - Guarulhos"), ("GIG", "Rio de Janeiro - Galeão"),
                         ("BSB", "Brasília"), ("SSA", "Salvador")],
    "estados unidos":   [("MIA", "Miami"), ("JFK", "Nova York - JFK"),
                         ("LAX", "Los Angeles"), ("MCO", "Orlando")],
    "eua":              [("MIA", "Miami"), ("JFK", "Nova York - JFK"),
                         ("LAX", "Los Angeles"), ("MCO", "Orlando")],
    "usa":              [("MIA", "Miami"), ("JFK", "Nova York - JFK"),
                         ("LAX", "Los Angeles"), ("MCO", "Orlando")],
    "canada":           [("YYZ", "Toronto"), ("YVR", "Vancouver"), ("YUL", "Montreal")],
    "franca":           [("CDG", "Paris - Charles de Gaulle"), ("ORY", "Paris - Orly")],
    "reino unido":      [("LHR", "Londres - Heathrow"), ("LGW", "Londres - Gatwick")],
    "inglaterra":       [("LHR", "Londres - Heathrow"), ("LGW", "Londres - Gatwick")],
    "alemanha":         [("FRA", "Frankfurt"), ("MUC", "Munique")],
    "espanha":          [("MAD", "Madri"), ("BCN", "Barcelona")],
    "portugal":         [("LIS", "Lisboa"), ("OPO", "Porto")],
    "italia":           [("FCO", "Roma - Fiumicino"), ("MXP", "Milão - Malpensa")],
    "holanda":          [("AMS", "Amsterdam")],
    "suica":            [("ZRH", "Zurique"), ("GVA", "Genebra")],
    "austria":          [("VIE", "Viena")],
    "belgica":          [("BRU", "Bruxelas")],
    "irlanda":          [("DUB", "Dublin")],
    "grecia":           [("ATH", "Atenas")],
    "turquia":          [("IST", "Istambul")],
    "emirados arabes":  [("DXB", "Dubai"), ("AUH", "Abu Dhabi")],
    "dubai":            [("DXB", "Dubai")],
    "japao":            [("NRT", "Tóquio - Narita"), ("HND", "Tóquio - Haneda")],
    "china":            [("PEK", "Pequim"), ("PVG", "Xangai - Pudong")],
    "coreia do sul":    [("ICN", "Seul")],
    "tailandia":        [("BKK", "Bangkok")],
    "indonesia":        [("DPS", "Bali - Denpasar"), ("CGK", "Jacarta")],
    "singapura":        [("SIN", "Cingapura")],
    "india":            [("BOM", "Mumbai"), ("DEL", "Nova Delhi")],
    "australia":        [("SYD", "Sydney"), ("MEL", "Melbourne"), ("BNE", "Brisbane")],
    "nova zelandia":    [("AKL", "Auckland")],
    "africa do sul":    [("JNB", "Joanesburgo"), ("CPT", "Cidade do Cabo")],
    "egito":            [("CAI", "Cairo")],
    "quenia":           [("NBO", "Nairóbi")],
    "argentina":        [("EZE", "Buenos Aires - Ezeiza"), ("AEP", "Buenos Aires - Aeroparque")],
    "chile":            [("SCL", "Santiago")],
    "peru":             [("LIM", "Lima")],
    "colombia":         [("BOG", "Bogotá"), ("MDE", "Medellín"), ("CTG", "Cartagena")],
    "mexico":           [("MEX", "Cidade do México"), ("CUN", "Cancún")],
    "cuba":             [("HAV", "Havana")],
    "venezuela":        [("CCS", "Caracas")],
    "equador":          [("UIO", "Quito"), ("GYE", "Guayaquil")],
    "bolivia":          [("VVI", "Santa Cruz de la Sierra")],
    "paraguai":         [("ASU", "Assunção")],
    "uruguai":          [("MVD", "Montevidéu")],
}


def _normalize(text: str) -> str:
    """Remove acentos e converte para minúsculo."""
    return unicodedata.normalize("NFD", text).encode("ascii", "ignore").decode().lower().strip()


def find_airports(query: str) -> List[dict]:
    """
    Busca aeroportos por país, cidade ou código IATA.
    Retorna lista de dicts com keys: code, name, label.
    """
    q = _normalize(query)

    # Busca direta por código IATA (ex: "GRU")
    if len(q) == 3 and q.isalpha():
        iata = q.upper()
        for airports in AIRPORTS.values():
            for code, name in airports:
                if code == iata:
                    return [{"code": code, "name": name, "label": f"{code} — {name}"}]
        return [{"code": iata, "name": iata, "label": iata}]

    results = []
    seen = set()

    # 1) Busca por país
    for country_key, airports in COUNTRIES.items():
        if q in country_key or country_key in q:
            for code, name in airports:
                if code not in seen:
                    seen.add(code)
                    results.append({"code": code, "name": name, "label": f"{code} — {name}"})

    if results:
        return results[:4]

    # 2) Busca por cidade / aeroporto
    for key, airports in AIRPORTS.items():
        if q in key or key in q:
            for code, name in airports:
                if code not in seen:
                    seen.add(code)
                    results.append({"code": code, "name": name, "label": f"{code} — {name}"})

    return results[:5]
