import googlemaps
import pandas as pd
import time
import os

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
API_KEY = os.getenv('MAPS_API_KEY') 
gmaps = googlemaps.Client(key=API_KEY)

archivo_zip = "codigos_postales_US.csv"
archivo_progreso = "progreso.txt"
archivo_salida = "reporte_acumulado.csv"
LIMITE_DIARIO = 100 

def buscar_salones(zip_code):
    all_results = []
    query = f"beauty salon in zip code {zip_code}, USA"
    try:
        response = gmaps.places(query=query)
        while True:
            results = response.get('results', [])
            for place in results:
                place_id = place.get('place_id')
                details = gmaps.place(
                    place_id=place_id, 
                    fields=['name', 'formatted_phone_number', 'website', 
                            'formatted_address', 'rating', 'user_ratings_total', 
                            'address_components']).get('result', {})
                
                address_components = details.get('address_components', [])
                estado = ""
                for component in address_components:
                    if 'administrative_area_level_1' in component['types']:
                        estado = component['long_name']  
                        break

                all_results.append({
                    'Nombre': details.get('name'),
                    'Estado': estado,
                    'Teléfono': details.get('formatted_phone_number'),
                    'Sitio Web': details.get('website'),
                    'Dirección': details.get('formatted_address'),
                    'Rating': details.get('rating'),
                    'Total Reseñas': details.get('user_ratings_total'),
                    'ZIP Code': zip_code
                })
            
            next_page_token = response.get('next_page_token')
            if not next_page_token: 
                break
            time.sleep(2) 
            response = gmaps.places(query=query, page_token=next_page_token)
    except Exception as e:
        print(f"Error procesando ZIP {zip_code}: {e}")
    return all_results

# ==========================================
# 2. PROCESAMIENTO LOGIC
# ==========================================
if os.path.exists(archivo_zip):
    df_zips = pd.read_csv(archivo_zip, dtype=str)
    zip_list = df_zips.iloc[:, 0].str.zfill(5).unique().tolist()
    total_zips = len(zip_list)

    # DETERMINAR SI ES LA PRIMERA VEZ (Carga masiva inicial)
    es_primera_vez = not os.path.exists(archivo_salida)

    if es_primera_vez:
        print("--- DETECTADA PRIMERA EJECUCIÓN: Procesando TODOS los códigos postales ---")
        indice_inicio = 0
        indice_fin = total_zips
    else:
        # Leer progreso guardado
        if os.path.exists(archivo_progreso):
            with open(archivo_progreso, "r") as f:
                try:
                    indice_inicio = int(f.read().strip())
                except:
                    indice_inicio = 0
        else:
            indice_inicio = 0
            
        if indice_inicio >= total_zips:
            print("¡Ciclo completado! Reiniciando desde el principio.")
            indice_inicio = 0
            
        indice_fin = min(indice_inicio + LIMITE_DIARIO, total_zips)
        print(f"--- MODO DIARIO: Procesando del {indice_inicio} al {indice_fin-1} ---")

    zips_a_procesar = zip_list[indice_inicio:indice_fin]
    resultados_totales = []
    
    for i, zip_hoy in enumerate(zips_a_procesar):
        print(f"[{i+1}/{len(zips_a_procesar)}] Buscando en ZIP: {zip_hoy}...")
        data = buscar_salones(zip_hoy)
        if data:
            resultados_totales.extend(data)
        time.sleep(0.5)

    # GUARDAR RESULTADOS
    if resultados_totales:
        df_final = pd.DataFrame(resultados_totales)
        header = not os.path.exists(archivo_salida)
        df_final.to_csv(archivo_salida, mode='a', index=False, header=header, encoding='utf-8-sig')
        print(f"Éxito: Se añadieron {len(resultados_totales)} registros.")

    # ACTUALIZAR PROGRESO (Solo relevante para el modo diario)
    nuevo_indice = 0 if indice_fin >= total_zips else indice_fin
    with open(archivo_progreso, "w") as f:
        f.write(str(nuevo_indice))
    
    print(f"Proceso terminado. Próximo inicio en índice: {nuevo_indice}")
else:
    print(f"Error: No se encontró el archivo {archivo_zip}")
