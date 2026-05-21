import googlemaps
import pandas as pd
import time
import os

# CONFIGURACIÓN 
API_KEY = os.getenv('MAPS_API_KEY') 
gmaps = googlemaps.Client(key=API_KEY)

def obtener_nombre_estado(place_id):
    """Obtiene el nombre completo del estado usando los componentes de la dirección."""
    try:
        # Pedimos address_components específicamente
        details = gmaps.place(place_id=place_id, fields=['address_components']).get('result', {})
        for component in details.get('address_components', []):
            if 'administrative_area_level_1' in component.get('types', []):
                return component.get('long_name') # Estados sin abreviatura
    except Exception:
        return None
    return None

def buscar_salones(zip_code):
    all_results = []
    query = f"beauty salon in zip code {zip_code}, USA"
    try:
        response = gmaps.places(query=query)
        while True:
            results = response.get('results', [])
            for place in results:
                place_id = place.get('place_id')
                
                # Campos extendidos para incluir address_components
                details = gmaps.place(place_id=place_id, 
                                     fields=['name', 'formatted_phone_number', 'website', 
                                             'formatted_address', 'rating', 'user_ratings_total', 
                                             'address_components']).get('result', {})
                
                # Extraer el estado completo de los componentes de este lugar
                estado_completo = None
                for component in details.get('address_components', []):
                    if 'administrative_area_level_1' in component.get('types', []):
                        estado_completo = component.get('long_name')
                        break
               #Los detalles y campos que aparecen en el excel
                all_results.append({
                    'Nombre': details.get('name'),
                    'Teléfono': details.get('formatted_phone_number'),
                    'Sitio Web': details.get('website'),
                    'Dirección': details.get('formatted_address'),
                    'Estado': estado_completo, # <--- Estado sin abreviar
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

# PROCESAMIENTO POR LOTES
archivo_zip = "codigos_postales_US.csv"
archivo_progreso = "progreso.txt"
archivo_salida = "reporte_acumulado.csv"
LIMITE_DIARIO = 500 # <--- Actualizado a 500/ termina en dos meses y medio

if os.path.exists(archivo_zip):
    df_zips = pd.read_csv(archivo_zip, dtype=str)
    zip_list = df_zips.iloc[:, 0].str.zfill(5).unique().tolist()
    total_zips = len(zip_list)

    indice_inicio = 0
    if os.path.exists(archivo_progreso):
        with open(archivo_progreso, "r") as f:
            try:
                indice_inicio = int(f.read().strip())
            except ValueError:
                indice_inicio = 0

    if indice_inicio >= total_zips:
        print("¡Fin de lista alcanzado! Reiniciando desde el principio.")
        indice_inicio = 0

    indice_fin = min(indice_inicio + LIMITE_DIARIO, total_zips)
    zips_a_procesar = zip_list[indice_inicio:indice_fin]

    print(f"--- Iniciando sesión: Procesando {len(zips_a_procesar)} códigos (del {indice_inicio} al {indice_fin-1}) ---")

    resultados_totales_hoy = []
    
    for i, zip_hoy in enumerate(zips_a_procesar):
        print(f"[{i+1}/{len(zips_a_procesar)}] Buscando en ZIP: {zip_hoy}...")
        data = buscar_salones(zip_hoy)
        if data:
            resultados_totales_hoy.extend(data)
        
        # Pausa para evitar bloqueos
        time.sleep(0.2)

    if resultados_totales_hoy:
        df_hoy = pd.DataFrame(resultados_totales_hoy)
        header = not os.path.exists(archivo_salida)
        df_hoy.to_csv(archivo_salida, mode='a', index=False, header=header, encoding='utf-8-sig')
        print(f"Éxito: Se guardaron {len(resultados_totales_hoy)} registros.")

    # Actualizar progreso
    with open(archivo_progreso, "w") as f:
        f.write(str(indice_fin if indice_fin < total_zips else 0))
    
    print(f"Progreso actualizado. Próximo inicio en índice: {indice_fin}")
else:
    print(f"Error: No se encontró el archivo {archivo_zip}")
