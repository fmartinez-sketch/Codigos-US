import requests
import pandas as pd
import time
import os

# CONFIGURACIÓN
archivo_zip = "codigos_postales_US.csv"
archivo_progreso = "progreso.txt"
archivo_salida = "reporte_acumulado.csv"
LIMITE_DIARIO = 100  # Bajamos a 100 para asegurar que no nos bloqueen por velocidad

def buscar_salones_osm(zip_code):
    all_results = []
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    # IMPORTANTE: Esto evita el error 406. Identifica tu bot.
    headers = {
        'User-Agent': 'BuscadorSalonesBot/1.0 (contacto: tu-usuario-github)',
        'Accept-Language': 'es,en;q=0.9'
    }
    
    overpass_query = f"""
    [out:json][timeout:30];
    area["postal_code"="{zip_code}"]["address:country"="US"]->.searchArea;
    (
      node["shop"~"beauty|hairdresser"](area.searchArea);
      way["shop"~"beauty|hairdresser"](area.searchArea);
      node["name"~"Salon",i](area.searchArea);
    );
    out center;
    """
    
    try:
        response = requests.get(overpass_url, params={'data': overpass_query}, headers=headers, timeout=40)
        
        if response.status_code == 200:
            data = response.json()
            for el in data.get('elements', []):
                tags = el.get('tags', {})
                calle = tags.get('addr:street', '')
                numero = tags.get('addr:housenumber', '')
                ciudad = tags.get('addr:city', '')
                estado = tags.get('addr:state', 'N/A')
                
                direccion = f"{numero} {calle}, {ciudad}".strip(", ")
                
                all_results.append({
                    'Nombre': tags.get('name', 'Sin nombre'),
                    'Teléfono': tags.get('phone') or tags.get('contact:phone') or 'N/D',
                    'Sitio Web': tags.get('website') or tags.get('contact:website') or 'N/D',
                    'Dirección': direccion if direccion else "Dirección no disponible",
                    'Estado': estado,
                    'Rating': 'N/A (OSM)',
                    'Total Reseñas': 'N/A (OSM)',
                    'ZIP Code': zip_code
                })
        elif response.status_code == 429:
            print(f"!!! Servidor saturado (429). Esperando 60 segundos en ZIP {zip_code}...")
            time.sleep(60)
        else:
            print(f"Error {response.status_code} en ZIP {zip_code}")
            
    except Exception as e:
        print(f"Error técnico en ZIP {zip_code}: {e}")
    return all_results

# --- PROCESO PRINCIPAL ---
if os.path.exists(archivo_zip):
    df_zips = pd.read_csv(archivo_zip, dtype=str)
    zip_list = df_zips.iloc[:, 0].str.zfill(5).unique().tolist()
    
    indice_inicio = 0
    if os.path.exists(archivo_progreso):
        with open(archivo_progreso, "r") as f:
            try:
                linea = f.read().strip()
                indice_inicio = int(linea) if linea else 0
            except:
                indice_inicio = 0

    if indice_inicio >= len(zip_list):
        print("¡Todos los códigos procesados! Reiniciando...")
        indice_inicio = 0

    indice_fin = min(indice_inicio + LIMITE_DIARIO, len(zip_list))
    zips_a_procesar = zip_list[indice_inicio:indice_fin]

    print(f"--- Iniciando sesión: {len(zips_a_procesar)} códigos (Índices {indice_inicio} a {indice_fin-1}) ---")

    for i, zip_hoy in enumerate(zips_a_procesar):
        print(f"[{i+1}/{len(zips_a_procesar)}] Buscando en ZIP: {zip_hoy}")
        data = buscar_salones_osm(zip_hoy)
        
        if data:
            df_temp = pd.DataFrame(data)
            header = not os.path.exists(archivo_salida) or os.stat(archivo_salida).st_size == 0
            df_temp.to_csv(archivo_salida, mode='a', index=False, header=header, encoding='utf-8-sig')
            print(f"   -> Guardados {len(data)} resultados.")
        
        # Actualizar progreso inmediatamente
        with open(archivo_progreso, "w") as f:
            f.write(str(indice_inicio + i + 1))
        
        # PAUSA VITAL para evitar el error 406/429
        time.sleep(3) 

    print("--- Sesión terminada exitosamente ---")
else:
    print(f"No se encontró el archivo {archivo_zip}")
