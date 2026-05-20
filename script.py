import googlemaps
import pandas as pd
import time
import os

# CONFIGURACIÓN
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
                details = gmaps.place(place_id=place_id, 
                                     fields=['name', 'formatted_phone_number', 'website', 
                                             'formatted_address', 'rating', 'user_ratings_total', 
                                             'address_components']).get('result', {})
                
                estado = "N/A"
                for component in details.get('address_components', []):
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
            if not next_page_token: break
            time.sleep(2)
            response = gmaps.places(query=query, page_token=next_page_token)
    except Exception as e:
        print(f"Error en ZIP {zip_code}: {e}")
    return all_results

# LÓGICA PRINCIPAL
if os.path.exists(archivo_zip):
    df_zips = pd.read_csv(archivo_zip, dtype=str)
    zip_list = df_zips.iloc[:, 0].str.zfill(5).unique().tolist()
    
    # Si el reporte no existe o es muy pequeño, procesar TODO una vez
    es_primera_vez = not os.path.exists(archivo_salida) or os.path.getsize(archivo_salida) < 100
    
    if es_primera_vez:
        print(f"--- INICIANDO CARGA MASIVA: {len(zip_list)} códigos ---")
        zips_a_procesar = zip_list
        indice_proximo = 0
    else:
        # Leer progreso para los 100 diarios
        try:
            with open(archivo_progreso, "r") as f:
                inicio = int(f.read().strip())
        except:
            inicio = 0
        
        fin = min(inicio + LIMITE_DIARIO, len(zip_list))
        zips_a_procesar = zip_list[inicio:fin]
        indice_proximo = 0 if fin >= len(zip_list) else fin
        print(f"--- MODO DIARIO: Procesando {inicio} al {fin} ---")

    resultados = []
    for z in zips_a_procesar:
        print(f"Buscando en ZIP: {z}")
        data = buscar_salones(z)
        resultados.extend(data)
        time.sleep(0.2)

    if resultados:
        df_new = pd.DataFrame(resultados)
        header = not os.path.exists(archivo_salida)
        df_new.to_csv(archivo_salida, mode='a', index=False, header=header, encoding='utf-8-sig')
        
        with open(archivo_progreso, "w") as f:
            f.write(str(indice_proximo))
        print(f"Éxito: {len(resultados)} filas guardadas.")
    else:
        print("No se encontraron resultados en la búsqueda.")
else:
    print(f"ERROR: No existe el archivo {archivo_zip}")
