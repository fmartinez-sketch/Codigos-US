import googlemaps
import pandas as pd
import time
import os

# --- CONFIGURACIÓN ---
# Usaremos 'Secrets' de GitHub para no exponer tu API KEY públicamente
API_KEY = os.getenv('MAPS_API_KEY') 
gmaps = googlemaps.Client(key=API_KEY)

def buscar_salones(zip_code):
    all_results = []
    query = f"beauty salon in zip code {zip_code}, USA"
    try:
        response = gmaps.places(query=query)
        while True:
            results = response.get('results', [])
            for place in results:
                place_id = place.get('place_id')
                details = gmaps.place(place_id=place_id, fields=['name', 'formatted_phone_number', 'website', 'formatted_address', 'rating', 'user_ratings_total']).get('result', {})
                all_results.append({
                    'Nombre': details.get('name'),
                    'Teléfono': details.get('formatted_phone_number'),
                    'Sitio Web': details.get('website'),
                    'Dirección': details.get('formatted_address'),
                    'Rating': details.get('rating'),
                    'Total Reseñas': details.get('user_ratings_total'),
                    'ZIP Code': zip_code
                })
            next_page_token = response.get('next_page_token')
            if not next_page_token: break
            time.sleep(2)
            response = gmaps.places(query=query, page_token=next_page_token)
    except Exception as e:
        print(f"Error: {e}")
    return all_results

# --- LÓGICA DIARIA ---
archivo_zip = "codigos_postales_US.csv"
archivo_progreso = "progreso.txt"
archivo_salida = "reporte_acumulado.csv"

if os.path.exists(archivo_zip):
    df_zips = pd.read_csv(archivo_zip, dtype=str)
    zip_list = df_zips.iloc[:, 0].str.zfill(5).unique().tolist()

    # Leer índice actual
    indice = 0
    if os.path.exists(archivo_progreso):
        with open(archivo_progreso, "r") as f:
            indice = int(f.read().strip())
    
    # Si terminamos la lista, reiniciar
    if indice >= len(zip_list):
        indice = 0

    zip_hoy = zip_list[indice]
    print(f"Procesando {zip_hoy} (Índice {indice})...")
    
    resultados = buscar_salones(zip_hoy)
    
    if resultados:
        df_hoy = pd.DataFrame(resultados)
        header = not os.path.exists(archivo_salida)
        df_hoy.to_csv(archivo_salida, mode='a', index=False, header=header, encoding='utf-8-sig')
        
        # Guardar siguiente índice para mañana
        with open(archivo_progreso, "w") as f:
            f.write(str(indice + 1))