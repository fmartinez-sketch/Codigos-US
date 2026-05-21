import requests
import pandas as pd
import time
import os

# CONFIGURACIÓN
archivo_zip = "codigos_postales_US.csv"
archivo_progreso = "progreso.txt"
archivo_salida = "reporte_acumulado.csv"
LIMITE_DIARIO = 500  # Puedes subirlo si quieres, ya que es gratis

def buscar_salones_osm(zip_code):
    """Busca salones usando la API de Overpass (OpenStreetMap)"""
    all_results = []
    
    # Query de Overpass: busca nodos y formas con la etiqueta 'beauty' o 'hair' en el ZIP dado
    overpass_url = "http://overpass-api.de/api/interpreter"
    
    # Buscamos negocios tipo 'beauty', 'hairdresser' o que tengan 'Salon' en el nombre
    overpass_query = f"""
    [out:json][timeout:25];
    area["postal_code"="{zip_code}"]["address:country"="US"]->.searchArea;
    (
      node["shop"~"beauty|hairdresser"](area.searchArea);
      way["shop"~"beauty|hairdresser"](area.searchArea);
      node["name"~"Salon",i](area.searchArea);
    );
    out center;
    
    
    try:
        response = requests.get(overpass_url, params={'data': overpass_query}, timeout=30)
        if response.status_code == 200:
            data = response.json()
            elements = data.get('elements', [])
            
            for el in elements:
                tags = el.get('tags', {})
                
                # Intentar construir la dirección
                calle = tags.get('addr:street', '')
                numero = tags.get('addr:housenumber', '')
                ciudad = tags.get('addr:city', '')
                estado = tags.get('addr:state', 'N/A')
                
                direccion_completa = f"{numero} {calle}, {ciudad}".strip(", ")
                
                all_results.append({
                    'Nombre': tags.get('name', 'Sin nombre'),
                    'Teléfono': tags.get('phone') or tags.get('contact:phone') or 'N/D',
                    'Sitio Web': tags.get('website') or tags.get('contact:website') or 'N/D',
                    'Dirección': direccion_completa if direccion_completa else "Dirección no disponible",
                    'Estado': estado,
                    'Rating': 'N/A (OSM)',
                    'Total Reseñas': 'N/A (OSM)',
                    'ZIP Code': zip_code
                })
        else:
            print(f"Error en API Overpass: {response.status_code}")
            
    except Exception as e:
        print(f"Error procesando ZIP {zip_code}: {e}")
        
    return all_results

# --- PROCESO PRINCIPAL ---
if os.path.exists(archivo_zip):
    # Cargar códigos postales
    df_zips = pd.read_csv(archivo_zip, dtype=str)
    zip_list = df_zips.iloc[:, 0].str.zfill(5).unique().tolist()
    total_zips = len(zip_list)

    # Leer progreso actual
    indice_inicio = 0
    if os.path.exists(archivo_progreso):
        with open(archivo_progreso, "r") as f:
            try:
                indice_inicio = int(f.read().strip())
            except:
                indice_inicio = 0

    # Si terminamos la lista, reiniciar
    if indice_inicio >= total_zips:
        indice_inicio = 0

    indice_fin = min(indice_inicio + LIMITE_DIARIO, total_zips)
    zips_a_procesar = zip_list[indice_inicio:indice_fin]

    print(f"Iniciando: Procesando {len(zips_a_procesar)} códigos (del {indice_inicio} al {indice_fin-1})")

    for i, zip_hoy in enumerate(zips_a_procesar):
        print(f"[{i+1}/{len(zips_a_procesar)}] Buscando en ZIP: {zip_hoy}...")
        
        data = buscar_salones_osm(zip_hoy)
        
        if data:
            df_temp = pd.DataFrame(data)
            # El header solo se pone si el archivo no existe o está vacío
            es_nuevo = not os.path.exists(archivo_salida) or os.stat(archivo_salida).st_size == 0
            df_temp.to_csv(archivo_salida, mode='a', index=False, header=es_nuevo, encoding='utf-8-sig')
            print(f"   -> Encontrados {len(data)} resultados.")
        
        # Guardar progreso después de cada código (por si se corta)
        with open(archivo_progreso, "w") as f:
            f.write(str(indice_inicio + i + 1))
        
        # Pausa de cortesía para no saturar el servidor gratuito de OSM
        time.sleep(1.5)

    print("¡Sesión completada con éxito!")
else:
    print(f"Error: No se encontró {archivo_zip}")
