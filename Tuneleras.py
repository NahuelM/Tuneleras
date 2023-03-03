import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pyproj


import dash
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, callback, State, dash_table
import psycopg2
from psycopg2.extensions import AsIs
import math
import numpy as np
from flask import send_from_directory
import pandas as pd


external_stylesheets = [
    {
        'href': 'static/styles.css',
        'rel': 'stylesheet'
    }
]

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, {
        'href': '../static/styles.css',
        'rel': 'stylesheet'
}, dbc.icons.BOOTSTRAP], title='Tuneleras')


csv_data_tramos = pd.read_csv('Datos.csv', delimiter = ',')
us_cities  =  pd.read_csv("https://raw.githubusercontent.com/plotly/datasets/master/us-cities-top-1k.csv")

def rotate_xMatriz(angle):
        """" Devuelve la matriz de rotacion que rota `angle` en el eje `x` """
        c = math.cos(angle)
        s = math.sin(angle)
        return [[1, 0, 0],
                [0, c, -s],
                [0, s, c]]

def rotate_yMatriz(angle):
    """" Devuelve la matriz de rotacion que rota `angle` en el eje `y` """
    c = math.cos(angle)
    s = math.sin(angle)
    return [[c, 0, s],
            [0, 1, 0],
            [-s, 0, c]]

def rotate_zMatriz(angle):
    """" Devuelve la matriz de rotacion que rota `angle` en el eje `z` """
    c = math.cos(angle)
    s = math.sin(angle)
    return [[c, -s, 0],
            [s, c, 0],
            [0, 0, 1]]

def crear_plano(puntos_array, datos):
    """" Devuelve un plano que pasa por tres puntos 
            PARAMETROS: `puntos_array` array de tres puntos por los que debe pasar el plano
    """
    v1Plano = np.array(puntos_array[1]) - np.array(puntos_array[0])
    v2Plano = np.array(puntos_array[2]) - np.array(puntos_array[0])
    #normal = np.cross(v1, v2)
    normalPlano = [v1Plano[1] * v2Plano[2] - v1Plano[2] * v2Plano[1],
                    v1Plano[2] * v2Plano[0] - v1Plano[0] * v2Plano[2],
                    v1Plano[0] * v2Plano[1] - v1Plano[1] * v2Plano[0]
                    ]
    a, b, c = normalPlano
    d = np.dot(normalPlano, puntos_array[0])
    #print(f"{a}x {b}y {c}z {d} = 0")

    # Genera una malla de puntos en el plano
    X, Y = np.meshgrid(np.linspace(0, datos[0][6], 10), np.linspace(-3, 3, 10))
    Z = (d - a*X - b*Y) / c
    return X, Y, Z

def crear_cilindro_mesh3d(Xcoord_C1, Ycoord_C1, ZCoord_C1, Xcoord_C2, Ycoord_C2, Zcoord_C2, radio_C1, radio_C2, color, opacity, info, eje, angle, name, trunco:bool, cota_inicial, cota_final, n):
        """
            Funcion que crea un cilindro a aprtir de dos circunferencias
            Parametros: `Xcoord_C1:` coordenada en X del centro de la circunferencia 1
                        `Xcoord_C2:` coordenada en X del centro de la circunferencia 1
                        `Ycoord_C1:` coordenada en Y del centro de la circunferencia 1
                        `Ycoord_C2:` coordenada en Y del centro de la circunferencia 1
                        `Zcoord_C1:` coordenada en Z del centro de la circunferencia 1
                        `Zcoord_C2:` coordenada en Z del centro de la circunferencia 1
                        `radio_C1:` radio de la circunferencia 1
                        `radio_C2:` radio de la circunferencia 2
                        `color:` color del cilindro
                        `opacity:` opacidad del cilindro
                        `info:` informacion que se verá si paso el mouse por el cilidnro en la grafica
                        `eje:` eje de rotacion 
                        `angle:` angulo en radianes para rotar
                        `name:` nombre del cilidro
                        `trunco:` bool-> si es verdadero truncara las coordenasdas en z de los vertices que esten por encima de la cota de terreno(les resta la distancia para que se siga dibujando bien)
                        
            IMPORTANTE:  Observar que la diferencia entre las coordenadas en Z de ambas circunferencias determina el largo del cilindro 
                         Al rotar el cilindro en algun eje tambien rotan sus ejes locales, por lo que algunas coordenas cambian (ejemplo, al rotarse en ele eje y, las coordenas x, z se intercambain)
            
            Return: La funcion regresa una lista con tres objetos
                    [0] Objeto Mesh3d 
                    [1] Array con las coordenadas de la circunferencia 1
                    [2] array con las coordenadas de la circunferencia 2
                        
        """
        x_c1 = [Xcoord_C1 + radio_C1*np.cos(t) for t in np.linspace(0, 2*np.pi, n)]
        y_c1 = [Ycoord_C1 + radio_C1*np.sin(t) for t in np.linspace(0, 2*np.pi, n)]
        z_c1 = [ZCoord_C1 for t in np.linspace(0, 2*np.pi, n)]

        x_c2 = [Xcoord_C2 + radio_C2*np.cos(t) for t in np.linspace(0, 2*np.pi, n)]
        y_c2 = [Ycoord_C2 + radio_C2*np.sin(t) for t in np.linspace(0, 2*np.pi, n)]
        z_c2 = [Zcoord_C2 for t in np.linspace(0, 2*np.pi, n)]
        

                
        #Roto las circunferencias 
        if(eje == 'y'):
            rotation_matrix = rotate_yMatriz(angle)
        else:
            rotation_matrix = rotate_xMatriz(angle)
            
        matrizC1 = list(zip(x_c1, y_c1, z_c1))
        matrizC1 = [list(t) for t in matrizC1]

        matrizC2 = list(zip(x_c2, y_c2, z_c2))
        matrizC2 = [list(t) for t in matrizC2]
        x_rc1 = []
        y_rc1 = []
        z_rc1 = []

        for row in matrizC1:
            rotated = np.dot(row, rotation_matrix)
            x_rc1.append(rotated[0])
            y_rc1.append(rotated[1])
            z_rc1.append(rotated[2])

        x_rc2 = []
        y_rc2 = []
        z_rc2 = []

        for row in matrizC2:
            rotated = np.dot(row, rotation_matrix)
            x_rc2.append(rotated[0])
            y_rc2.append(rotated[1])
            z_rc2.append(rotated[2])
            
            
        ####################################################################################
        # TRUNCO RED ZONE A COTA DE TERRENO, PARA QUE LA ZONA ROJA NO SOBREPASE EL TERRENO #
        ####################################################################################
        if(trunco):
            for i in range(0, len(z_rc1)):
                if(z_rc1[i] > cota_inicial[0][0]):
                    z_rc1[i] = z_rc1[i] - (z_rc1[i] - cota_inicial[0][0])

            
            for i in range(0, len(z_rc2)):
                if(z_rc2[i] > cota_final[0][0]):
                    z_rc2[i] = z_rc2[i] - (z_rc2[i] - cota_final[0][0])

        # Coordenadas de los vértices
        xcy1 = []
        ycy1 = []
        zcy1 = []

        for k in range(0, n, 1):
            xcy1 = xcy1 + [x_rc1[k], x_rc2[k]]
            ycy1 = ycy1 + [y_rc1[k], y_rc2[k]]
            zcy1 = zcy1 + [z_rc1[k], z_rc2[k]]

        ViCy1 = []
        VjCy1 = []
        VkCy1 = []

        for i in range((n*2) - 2):
            ViCy1.append(i % ((n*2) - 1))
            VjCy1.append((i+1) % ((n*2) - 2))
            VkCy1.append(((i+1) % ((n*2) - 2)) + 1)
            
        # Crear una malla de la caras laterales del cilindro
        return [go.Mesh3d(x = xcy1, y = ycy1, z = zcy1, i = ViCy1, j = VjCy1, k = VkCy1, color = color, opacity = opacity, flatshading = True, intensitymode = 'cell', hovertemplate=info, name = name), [x_rc1, y_rc1, z_rc1], [x_rc2, y_rc2, z_rc2]]

def make_map(tramos_csv, id):
    datos_CSV = tramos_csv.iloc[int(id)][0:16]
    datos = [datos_CSV]
    x = float(datos[0][12])
    y = float(datos[0][13])
    hover_data = [x, y]
    transformer = pyproj.Transformer.from_crs("EPSG:32721", "EPSG:4326")
    lat, lon = transformer.transform(x, y)
    lat_array = [str(lat)]
    lon_array = [str(lon)]
    center_lat = lat
    center_lon = lon
    data_frame =  pd.DataFrame({'id':[datos[0][0]],
                                'Tipo de tramo':[datos[0][1]],
                                'Tipo de seccion':[datos[0][2]], 
                                'zarriba':[datos[0][5]],
                                'zabajo':[datos[0][6]],
                                'lat':[lat],
                                'lon':[lon],
                                'x':[datos[0][12]],
                                'y':[datos[0][13]]})
    x = float(datos[0][14])
    y = float(datos[0][15])
    hover_data.append(x)
    hover_data.append(y)
    lat, lon = transformer.transform(x, y)  
    lat_array.append(str(lat))
    lon_array.append(str(lon))
    center_lat += lat
    center_lon += lon
    nueva_fila = pd.DataFrame({'id':[datos[0][0]],
                                'Tipo de tramo':[datos[0][1]],
                                'Tipo de seccion':[datos[0][2]], 
                                'zarriba':[datos[0][5]],
                                'zabajo':[datos[0][6]],
                                'lat':[lat],
                                'lon':[lon],
                                'x':[datos[0][14]],
                                'y':[datos[0][15]]})

    data_frame = pd.concat([data_frame, nueva_fila])    

    text_data = ['aa', 'AA']
    if(datos[0][6] == 'IMP'):
        text_data = ['AA', 'aa']

    map_tramo = go.Scattermapbox(
        lat = lat_array,
        lon = lon_array,
        mode = 'lines+text+markers',
        marker = go.scattermapbox.Marker(
            size = 9,
            color = 'rgba(200, 30, 100, 1)',
            
        ),
        text = text_data,
        textposition = 'bottom center',
        hoverinfo = 'text'
    )
    
    map_tunelera = go.Scattermapbox(
        lat = lat_array,
        lon = lon_array,
        mode = 'lines+text+markers',
        marker = go.scattermapbox.Marker(
            size = 9,
            color = 'rgba(10, 70, 80, 1)',
            
        ),
        text = text_data,
        textposition = 'bottom center',
        hoverinfo = 'text'
                        
    )
    fig = go.Figure(data = [map_tramo, map_tunelera])
    fig.update_layout(
        mapbox = dict(
            accesstoken='pk.eyJ1IjoibmFodWVsMDAwIiwiYSI6ImNsZW11MGQ2YjAweXUzcnIxaHp4MTF2NGgifQ.aLPRn5aR6GNJ3QDIKbhFeg',
            style = 'light', 
            center = go.layout.mapbox.Center(
                lat = center_lat/2,
                lon = center_lon/2
            ),
            zoom = 18
        ),
        margin = {"r":0,"t":1,"l":0,"b":0}
    )
    return fig

def create_graph(id_tramo, diametro_tunelera, profundidad_tunelera, dis_esquina):
    app.server.my_variable = 'Initial value'
    app.server.danger_type = ''

    datos_CSV = csv_data_tramos.iloc[int(id_tramo)][1:8]
    datos = [datos_CSV]
    
    cota_inicial_CSV = csv_data_tramos.iloc[int(id_tramo)][8:10]
    cota_final_CSV = csv_data_tramos.iloc[int(id_tramo)][10:12]
    cota_inicial = [cota_inicial_CSV]
    cota_final = [cota_final_CSV]
    coords_puntos_tapas = csv_data_tramos.iloc[int(id_tramo)][12:16]
    
    
    if cota_inicial[0][0] == 0 and cota_final[0][0] == 0:
        fig = go.Figure(data=[])
        app.server.my_variable = 'Danger!!'
        app.server.danger_type = 'Danger01'

    elif (cota_inicial[0][0] == 0):
        fig = go.Figure(data=[])
        app.server.my_variable = 'Danger!!'
        app.server.danger_type = 'Danger02'

    elif cota_final[0][0] == 0:
        fig = go.Figure(data=[])
        app.server.my_variable = 'Danger!!'

    diam = float(datos[0][2])
    zabajo = float(datos[0][5])
    zarriba = float(datos[0][4])

    color_colector_Hex = '#808080'
    color_colector_Rgba = 'rgba(128, 128, 128, .5)'

    if (datos[0][1] == 'ART'):
        espesor_arriba = 0.4
        espesor_abajo = 0.5
        factor = 4
    else:
        if (float(datos[0][3]) > 0.7):
            espesor_arriba = 0.2
        else:
            espesor_arriba = 0.1
        factor = 2
        espesor_abajo = 0.3


    y_redzone_1 = zarriba - factor*diam - espesor_abajo
    y_redzone_2 = zabajo - factor*diam - espesor_abajo

    y_redzone_12 = diam + zarriba + factor*diam + espesor_arriba
    y_redzone_22 = diam + zabajo + factor*diam + espesor_arriba

    a = float(datos[0][4]) - float(datos[0][5])
    b = float(datos[0][6])
    res = b * b - (a * a)
    if (res > 0):
        xf = math.sqrt(res)
    else:
        app.server.my_variable = 'Danger!!'
        app.server.danger_type = 'Danger01'
        xf = .5

    

    # Coordenadas del centro de la circunferencia
    x1 = ((zarriba + diam + espesor_arriba) + (zarriba - espesor_abajo)) / 2 #Las coordenadas en x pasan a ser la altura al rotar los objectos, ya que rotan en local y sus ejes tambien rotan
    y1 = 0
    z1 = 0 #Las coordenadas en z pasan a ser el eje x

    x2 = ((zabajo + diam + espesor_arriba) + (zabajo - espesor_abajo)) / 2
    y2 = 0
    z2 = -xf

    x3 = (y_redzone_1 + y_redzone_12) / 2
    y3 = 0
    z3 = 0

    x4 = (y_redzone_2 + y_redzone_22) / 2
    y4 = 0
    z4 = -xf

    n = 31
    # Radios de las circunferencia
    r1 = (zarriba + diam + espesor_arriba) - x1
    r2 = (zabajo + diam + espesor_arriba) - x2
    r3 = y_redzone_1 - x3
    r4 = y_redzone_2 - x4

    ###################################    ######################################################################################################
    # FUNCION PARA CREAR CILINDROS 3D #    #RETORNA UNA MESH3D DEL CILINDRO Y DOS MATRICES CON LAS COORDS DE LAS CIRCUNFERENECIAS QUE LO FORMAN #
    ###################################    ######################################################################################################
    

    
    caras_lados_cilindro_colector = crear_cilindro_mesh3d(x1, y1, z1, x2, y2, z2, r1, r2, 'rgba(181, 181, 181, 1)', 1, 'Colector', 'y', math.pi / 2, name = 'ladoTramo1', trunco = False, cota_final = cota_final, cota_inicial = cota_inicial, n = n)
    caras_lados_cilindro_colector1 = crear_cilindro_mesh3d(x1, y1, z1, x2, y2, z2, r1 - .1, r2 - .1, 'rgba(181, 181, 181, 1)', 1, 'Colector', 'y', math.pi / 2, name = 'ladoTramo2', trunco = False, cota_final = cota_final, cota_inicial = cota_inicial, n = n)
    caras_lados_cilindro_redzone = crear_cilindro_mesh3d(x3, y3, z3, x4, y4, z4, r3, r4, 'rgba(255, 66, 85, 1)', .25, 'Zona no permitida para perforaciones', 'y', math.pi / 2, name = 'ladoRD', trunco = True, cota_final = cota_final, cota_inicial = cota_inicial, n = n)
    
    border_colector_C1 = go.Scatter3d(x = caras_lados_cilindro_colector[1][0], y = caras_lados_cilindro_colector[1][1], z = caras_lados_cilindro_colector[1][2], mode = 'lines', marker = dict(color = 'gray'), hovertemplate='-')
    border_colector_C2 = go.Scatter3d(x = caras_lados_cilindro_colector[2][0], y = caras_lados_cilindro_colector[2][1], z = caras_lados_cilindro_colector[2][2], mode = 'lines', marker = dict(color = 'gray'), hovertemplate='-')
    
    border_colector1_C1 = go.Scatter3d(x = caras_lados_cilindro_colector1[1][0], y = caras_lados_cilindro_colector1[1][1], z = caras_lados_cilindro_colector1[1][2], mode = 'lines', marker = dict(color = 'gray'), hovertemplate='-')
    border_colector1_C2 = go.Scatter3d(x = caras_lados_cilindro_colector1[2][0], y = caras_lados_cilindro_colector1[2][1], z = caras_lados_cilindro_colector1[2][2], mode = 'lines', marker = dict(color = 'gray'), hovertemplate='-')
    
    border_redzone_C1 = go.Scatter3d(x = caras_lados_cilindro_redzone[1][0], y = caras_lados_cilindro_redzone[1][1], z = caras_lados_cilindro_redzone[1][2], mode = 'lines', marker = dict(color = 'rgba(181, 0, 24, 1)'), hovertemplate='-')
    border_redzone_C2 = go.Scatter3d(x = caras_lados_cilindro_redzone[2][0], y = caras_lados_cilindro_redzone[2][1], z = caras_lados_cilindro_redzone[2][2], mode = 'lines', marker = dict(color = 'rgba(181, 0, 24, 1)'), hovertemplate='-')
    #propuesta tunelera más abajo
    # puntosPropuestaTuneleraAbajo = [(0, 0, cota_inicial[0][0]-(profundidad_tunelera+0.5*diametro_tunelera)), 
    #                                 (datos[0][6] / 2, 15, ((cota_inicial[0][0]-(profundidad_tunelera+0.5*diametro_tunelera) + cota_final[0][0]-(profundidad_tunelera+0.5*diametro_tunelera))/2)), 
    #                                 (datos[0][6], 0, cota_final[0][0]-(profundidad_tunelera+0.5*diametro_tunelera))
    #                                 ]

    # #propuesta tunelera más arriba
    # puntos_propuesta_tunelera_Arriba = [(0, 0, cota_inicial[0][0]-(profundidad_tunelera-0.5*diametro_tunelera)), 
    #                                     (datos[0][6] / 2, 15, ((cota_inicial[0][0]-(profundidad_tunelera-0.5*diametro_tunelera) + cota_final[0][0]-(profundidad_tunelera-0.5*diametro_tunelera))/2)), 
    #                                     (datos[0][6], 0, cota_final[0][0]-(profundidad_tunelera-0.5*diametro_tunelera))
    #                                     ]
    #DIBUJA COTA DE TERRENO
    puntos_plano_terreno = [(0, 0, cota_inicial[0][0]), 
                            (datos[0][6] / 2, 15, (cota_inicial[0][0] + cota_final[0][0]) / 2), 
                            (datos[0][6], 0, cota_final[0][0])
                            ]
    lado = 2*(puntos_plano_terreno[2][2] - (y_redzone_22 + 2*r4))

    def crear_plano_mesh3d(puntos_plano, color, opcacity, info, offset_Z):
        #Creo los 4 vertices del cuadrado que representan una porcion del plano que pasa por los puntos que definen al mismo 
        vertcices_planoArray = [(puntos_plano[0][0], puntos_plano[0][1] + (lado/2), puntos_plano[0][2] + offset_Z),
                                (puntos_plano[2][0], puntos_plano[2][1] + (lado/2), puntos_plano[2][2] + offset_Z),
                                (puntos_plano[0][0], puntos_plano[0][1] - (lado/2), puntos_plano[0][2] + offset_Z),
                                (puntos_plano[2][0], puntos_plano[2][1] - (lado/2), puntos_plano[2][2] + offset_Z)
                               ]
        
        x = [v[0] for v in vertcices_planoArray]
        y = [v[1] for v in vertcices_planoArray]
        z = [v[2] for v in vertcices_planoArray]
        i = [0, 2]
        j = [1, 3]
        k = [2, 1]
        return go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k, color=color, opacity=opcacity, lighting = dict(
            ambient = 0.5,
            diffuse = .1,
            specular = .5,
            roughness = 0.5,
            fresnel = .1,
            vertexnormalsepsilon = 1e-20,
            facenormalsepsilon = 0
        ), 
        lightposition = dict(x = 0, y = 0, z = 10000),
        intensitymode = 'cell',
        flatshading = True,
        hovertemplate=info)

    ###########################################
    # FUNCION PARA CREAR PRISMAS RECTOS       #
    ###########################################
    def crear_cube_mesh3d(puntos_plano, color, opcacity, info, extrude_distance):
        #Creo los 4 vertices del cuadrado que representan una porcion del plano que pasa por los puntos que definen al mismo 
        vertcicesPlanoArray = [(puntos_plano[0][0], puntos_plano[0][1] + (lado/2), puntos_plano[0][2]),
                               (puntos_plano[2][0], puntos_plano[2][1] + (lado/2), puntos_plano[2][2]),
                               (puntos_plano[0][0], puntos_plano[0][1] - (lado/2), puntos_plano[0][2]),
                               (puntos_plano[2][0], puntos_plano[2][1] - (lado/2), puntos_plano[2][2]),
                               (puntos_plano[0][0], puntos_plano[0][1] + (lado/2), puntos_plano[0][2] + extrude_distance),
                               (puntos_plano[2][0], puntos_plano[2][1] + (lado/2), puntos_plano[2][2] + extrude_distance),
                               (puntos_plano[0][0], puntos_plano[0][1] - (lado/2), puntos_plano[0][2] + extrude_distance),
                               (puntos_plano[2][0], puntos_plano[2][1] - (lado/2), puntos_plano[2][2] + extrude_distance)
                              ]
        x = [v[0] for v in vertcicesPlanoArray]
        y = [v[1] for v in vertcicesPlanoArray]
        z = [v[2] for v in vertcicesPlanoArray]
        i = [0, 2, 4, 6, 0, 4, 1, 7, 3, 2, 2, 4]
        j = [1, 3, 5, 7, 4, 5, 3, 3, 7, 6, 6, 0]
        k = [2, 1, 6, 5, 1, 1, 5, 5, 2, 7, 0, 6]
        return go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k, color=color, opacity=opcacity, 
        lightposition = dict(x = 1000, y = 0, z = 10000),
        intensitymode = 'cell',
        flatshading = True,
        hovertemplate=info
        )

    
    #####################################################
    ######## DIBUJO CARAS FRONTALES DE EL COLECTOR ######
    #####################################################
    
    xAux = caras_lados_cilindro_colector[0].x + caras_lados_cilindro_colector1[0].x
    yAux = caras_lados_cilindro_colector[0].y + caras_lados_cilindro_colector1[0].y
    zAux = caras_lados_cilindro_colector[0].z + caras_lados_cilindro_colector1[0].z

    iAux = np.concatenate((np.array(np.linspace(0, (n*2)-2, n)), np.array(np.linspace(1, (n*2)-1, n))))
    jAux = np.concatenate((np.array(np.linspace((n*2), (n*4)-2, n)), np.array(np.linspace((n*2)+1, (n*4)-1, n))))
    kAux = np.concatenate((np.array(np.linspace(2, (n*2), n)), np.array(np.linspace(3, (n*2)+1, n))))

    iAux1 = np.concatenate((np.linspace((n*2)+1, (n*4)-3, n-1), np.linspace((n*2), (n*4)-4, n-1)))#[62, 64, 66, 68]
    jAux1 = np.concatenate((np.linspace(3, (n*2)-1, n-1), np.linspace(2, (n*2)-2, n-1))) #[2, 4, 6, 8]
    kAux1 = np.concatenate((np.linspace((n*2)+3, (n*4)-1, n-1), np.linspace((n*2)+2, (n*4)-2, n-1))) #[64, 66, 68, 70]

    frente_colector = go.Mesh3d(x=xAux, y=yAux, z=zAux, i = np.concatenate((iAux1, iAux)), j = np.concatenate((jAux1, jAux)), k = np.concatenate((kAux1, kAux)), color = 'rgba(181, 181, 181, 1)', opacity = 1, flatshading = True, intensitymode = 'cell', hovertemplate='Colector')
    
    ##############################################
    #######    ANIMACION DE TUNELERA    ##########
    ##############################################
    #region ANIMACION
    frames_anim = None
    x_dis_esquina = 0
    profundidad_reltaiva = profundidad_tunelera
    anotacion_error = None
    pendiente2 = -(cota_final[0][0] - cota_inicial[0][0]) / (0 - xf) 
    def recta_terreno(X):
        """ recta que pasa los puntos de las cotas de terreno, cota_inicial y cota_final Devuelve la imagen de X en z"""
        return pendiente2 * X - (pendiente2*0) + (cota_inicial[0][0])
    punto_aux1 = go.Scatter3d(x = [0, dis_esquina, xf], y = [0, 0, 0], z = [recta_terreno(0), recta_terreno(dis_esquina), recta_terreno(xf)])
    #if (dis_esquina >= 0):
    x_dis_esquina = dis_esquina
    # if(datos[0][0] == 'IMP'):
    #     x_dis_esquina = math.fabs(xf - dis_esquina)    
    
    
    # pendiente = (Z1 - Z0) / (X1 - X0)
    # Z = mX - mX1 + Z1
    pendiente = (x4 - x3) / (y3 - z4) #esto esta bien, aunque parezca que no
    pendiente1 = ((x4+r4) - (x3+r3)) / (y3 - z4)
    
    
    def recta(X):  
        """ recta que pasa por los centros de las circunferencias del colector Devuelve la imagen de X en z"""
        return  pendiente * X - (pendiente*y3) + x3
    
    def recta1(X):
        """ recta que pasa por los puntos mas abajos(minimos) de la red zone Devuelve la imagen de X en z"""
        return pendiente1 * X - (pendiente1*y3) + (x3+r3) 
    

    
    #Radio de circunferencia para calcular interseccion
    radio_circ_temporal1 = (recta1(x_dis_esquina + diametro_tunelera/2)) - (recta(x_dis_esquina + diametro_tunelera/2))
    radio_circ_temporal2 = (recta1(x_dis_esquina - diametro_tunelera/2)) - (recta(x_dis_esquina - diametro_tunelera/2))
    
    profundidad_reltaiva = recta_terreno(x_dis_esquina) - (profundidad_tunelera + diametro_tunelera/2)
    
    print(str(recta_terreno(x_dis_esquina)))
    print(str(recta_terreno(x_dis_esquina) - (profundidad_tunelera + diametro_tunelera/2)))

    cilindro_temporal_interseccion = crear_cilindro_mesh3d(recta(x_dis_esquina + diametro_tunelera/2), 0,  -(x_dis_esquina + diametro_tunelera/2), recta(x_dis_esquina - diametro_tunelera/2), 0,  -(x_dis_esquina - diametro_tunelera/2), radio_circ_temporal1, radio_circ_temporal2, 'orange', 1, 'temporal', 'y', math.pi / 2, 'name', False, cota_final = cota_final, cota_inicial = cota_inicial, n = n)
    Z_cota = np.concatenate((cilindro_temporal_interseccion[1][2], cilindro_temporal_interseccion[2][2])) #concatenacion de arrays con las coordenadas en Z de las circunferencias que forman el cildro
    Y_cota = np.concatenate((cilindro_temporal_interseccion[1][1], cilindro_temporal_interseccion[2][1])) #concatenacion de arrays con las coordenadas en Y de las circunferencias que forman el cildro

    cant_frames = 35
    switch_aux = 1 if profundidad_reltaiva > recta(x_dis_esquina) else -1
    
    #O(cantidad de vertices de circunferencia tunelera * cantidad de vertices de circunferencia cilindro rojo * 2) cantidad de iteraciones
    def interseccion_de_cilindros(cilindro_mesh) -> bool:
        """
            Devuelve True si el mesh pasado como parametro intersecta en algun punto al mesh de red zone
        """
        l = 0
        no_intersecta = True
        while l < len(cilindro_mesh[2][2]) and no_intersecta:
            i = 0
            while i < len(Z_cota) and no_intersecta:
                coord_vertice_enZ = cilindro_mesh[2][2][l] #vertice del cilindro tunelera
                coord_vertice_enY = cilindro_mesh[2][1][l]
                no_intersecta = (coord_vertice_enZ - Z_cota[i])*switch_aux > 0 or (coord_vertice_enY - Y_cota[i]) > 0
                i += 1
            l += 1
        return no_intersecta
    
    
    frames_anim = []
    
    
    #### ANIMACION DE CAMARA
    # Obtiene las coordenadas de la cámara

    lado_cam_movment = 1 if x_dis_esquina > xf/2 else -1
    X_cam_path = np.linspace(0, 3.5*lado_cam_movment, cant_frames)
    Y_cam_path = np.linspace(3, 0.5, cant_frames)
    Z_cam_path = 0.1
    for t in range(cant_frames):
        frame_cam = dict(layout=dict(scene=dict(camera=dict(eye=dict(x=X_cam_path[t], y=Y_cam_path[t], z=Z_cam_path), center = dict(x = 0, y = 0, z = 0)))))
        frames_anim.append(frame_cam)
    

    k = 0
    paso = ((-lado/1.5) - (lado/1.5)) / cant_frames
    h = lado/1.5
    cilindro_Frame = crear_cilindro_mesh3d(x_dis_esquina, -profundidad_reltaiva, lado/1.5, x_dis_esquina, -profundidad_reltaiva, h, diametro_tunelera/2, diametro_tunelera/2, 'rgba(204, 204, 204, .8)', 1, 'Tunelera', 'x', math.pi / 2, name='propTun', trunco = False, cota_final = cota_final, cota_inicial = cota_inicial, n = n)
    
    while k <= cant_frames and interseccion_de_cilindros(cilindro_Frame):
        frame = go.Frame(data = [cilindro_Frame[0]])
        cilindro_Frame = crear_cilindro_mesh3d(x_dis_esquina, -profundidad_reltaiva, lado/1.5, x_dis_esquina, -profundidad_reltaiva, h, diametro_tunelera/2, diametro_tunelera/2, 'rgba(204, 204, 204, 8)', 1, 'Tunelera', 'x', math.pi / 2, name='propTun', trunco = False, cota_final = cota_final, cota_inicial = cota_inicial, n = n)
        frames_anim.append(frame)
        h += paso
        k += 1

    if k < cant_frames:
        punto_de_interseccion_tun_redzone = go.Scatter3d(x = [x_dis_esquina], y = [h - paso], z = [profundidad_reltaiva], marker=dict(color = 'red', symbol = 'x')) 
        anotacion_error = go.Layout( 
                    annotations = [go.layout.Annotation(x = 0, 
                                    y = .1, 
                                    text = 'Error!!!.<br>Interseccion de tunelera con zona <br>prohibida para perforaciones', 
                                    arrowcolor = "red",
                                    font = dict(size = 25),
                                    height = 100,
                                    width = 500, 
                                    valign = 'middle', 
                                    arrowsize = 1,
                                    align = 'center',
                                    arrowwidth = 1,
                                    arrowhead = 1,
                                    xanchor = 'left',
                                    bordercolor = 'rgba(220, 50, 50, 1)', 
                                    bgcolor = 'rgba(230, 0, 0, .3)',
                                    )
                                    ]
                    )
                
        frame = go.Frame(data = [punto_de_interseccion_tun_redzone, cilindro_Frame[0]], layout = anotacion_error)
        frames_anim.append(frame)
    else:
        anotacion_exito = go.Layout( 
                    annotations = [go.layout.Annotation(x = 0, 
                                    y = .1, 
                                    text = 'Tunelera permitida', 
                                    arrowcolor = "green",
                                    font = dict(size = 25),
                                    height = 100,
                                    width = 500, 
                                    valign = 'middle', 
                                    align = 'center',
                                    arrowsize = 1,
                                    arrowwidth = 1,
                                    arrowhead = 1,
                                    xanchor = 'left',
                                    bordercolor = 'rgba(50, 200, 50, 1)', 
                                    bgcolor = 'rgba(50, 220, 50, .3)',

                                    )
                                    ]
                    )
                
        frame = go.Frame(data = [cilindro_Frame[0]], layout=anotacion_exito)
        frames_anim.append(frame)
            
    #endregion
            
    #########################################################
    #### CREO FIGURA 3D QUE CONTIENE TODAS LOS GRAFICOS #####
    #########################################################
    punto_fantasma = go.Scatter3d(x = [], y = [], z = []) #Por alguna razon al reproducir la animacion empieza a borrar los objetos de la lista data desde el principio, entonces creo puntos fantasmas para que borre esos

        
    direccion_agua_arrow = go.Scatter3d(x = [0 - 1 , xf + 1], y = [0, 0], z = [zarriba, zabajo],
                                   mode = 'lines+markers+text',
                                   line = dict(color='blue', width=5),
                                   text = ['AA', 'aa'],
                                   textposition = 'top center', 
                                   marker = dict(size = 3))

    fig = go.Figure(data = [ punto_fantasma, punto_fantasma, caras_lados_cilindro_redzone[0], caras_lados_cilindro_colector[0], caras_lados_cilindro_colector1[0], crear_cube_mesh3d(puntos_plano_terreno, 'rgba(150, 150, 163, 1)', 1, 'Superficie', .18), crear_plano_mesh3d(puntos_plano_terreno, 'rgb(128, 128, 138)', 1, '', .183),
                            frente_colector, direccion_agua_arrow,
                            border_colector_C1, border_colector_C2, border_colector1_C1, border_colector1_C2, border_redzone_C1, border_redzone_C2], 
                            frames = frames_anim, 
                            layout = go.Layout(updatemenus = [dict(
                                                type = "buttons",
                                                buttons = [dict(label = "Play", 
                                                                method = "animate",
                                                                args = [None, dict(frame = dict(duration = 5, redraw = True),
                                                                                   transition = dict(duration = 4) 
                                                                                   )
                                                                        ]
                                                                )
                                                           ]
                                                )],
                                                #eye es la posicion y center el punto al que mira
                                                scene_camera = dict(eye=dict(x=4, y=4, z=.1))
                                                )
                    )

    if (profundidad_tunelera > 0):
        
        cilindro_tunelera = crear_cilindro_mesh3d(x_dis_esquina, -profundidad_reltaiva, lado/1.5, x_dis_esquina, -profundidad_reltaiva, -lado/1.5, diametro_tunelera/2, diametro_tunelera/2, 'rgba(204, 204, 204, .15)', 1, 'Tunelera', 'x', math.pi / 2, name='propTun', trunco = False, cota_final = cota_final, cota_inicial = cota_inicial, n = n)
        border_cilindro_tun = go.Scatter3d(x = cilindro_tunelera[1][0], y = cilindro_tunelera[1][1], z = cilindro_tunelera[1][2], mode = 'lines', marker = dict(color = 'black'))
        border_cilindro_tun1 = go.Scatter3d(x = cilindro_tunelera[2][0], y = cilindro_tunelera[2][1], z = cilindro_tunelera[2][2], mode = 'lines', marker = dict(color = 'black'))
        linea_trayectoria_tun = go.Scatter3d(x = [x_dis_esquina, x_dis_esquina], y = [lado/1.5, -lado/1.5], z = [profundidad_reltaiva, profundidad_reltaiva], mode='lines+markers',  marker = dict(color = 'black', size = 5), line=dict(dash = 'longdashdot'))
        fig.add_trace(cilindro_tunelera[0])
        fig.add_trace(border_cilindro_tun)
        fig.add_trace(border_cilindro_tun1)
        fig.add_trace(linea_trayectoria_tun)
      
    
    ##############################################
    #######    ANOTACIONES              ##########
    ##############################################

    anotaciones = [
    #                     dict(x = xf, 
    #                     y = 0, 
    #                     z = cota_inicial[0][0], 
    #                     text = 'Largo de colector: ' + str(round(xf, 2)) + 'm' + '<br>Aguas arriba', 
    #                     arrowcolor = "black",
    #                     arrowsize = 2,
    #                     arrowwidth = 1,
    #                     arrowhead = 1,
    #                     xanchor = 'left',
    #                     bordercolor = '#969696', bgcolor = '#cccccc', align = 'left'
    #                     )
                    ]
    anotacion_tunelera = dict(x = x_dis_esquina, y = -lado/1.5, z = cota_inicial[0][0] - profundidad_tunelera, text = 'Camino para tunelera<br>Profundidad: ' + str(profundidad_tunelera) + 'm' + '<br>Diametro: ' + str(diametro_tunelera) + 'm',
                                bordercolor = '#969696', bgcolor = '#cccccc', align = 'left' )
    if(profundidad_tunelera > 0):
        anotaciones.append(anotacion_tunelera)
        
    fig.update_xaxes(layer = 'below traces')
    fig.update_yaxes(layer = 'below traces')


    fig.update_layout(
        title = dict(text ='Representación 3D', x = .5, y = .9, xanchor = 'center', yanchor = 'top'), 
        showlegend = False,
        scene = dict(annotations = anotaciones,
                     aspectmode='data',
                     xaxis_showgrid=False, yaxis_showgrid=False, zaxis_showgrid=False,
                     xaxis = dict(showticklabels = False),
                     yaxis = dict(showticklabels = False),
                     xaxis_title = " ",
                     yaxis_title = " ",
                     zaxis_title = 'Cota',
                     ),
        margin = {"r":5,"t":5,"l":5,"b":5}
       
    )
    fig.layout.height = 645
    

    #################################################################
    ##### CREA LA GRAFICA 2D ########################################
    #################################################################
    def crear2D():
        """Crea la grafica 2d que esta a la derecha en el dibujo """
        
        #COTA DE TERRENO
        terreno = go.Scatter(x = [0, xf], y = [cota_inicial[0][0], cota_final[0][0]],  marker = dict(color = 'gray'), mode = 'lines', name = 'Superficie')
        
        # DIBUJA TRAMO
        tramo_arriba = go.Scatter(x = [0, xf], y = [zarriba+diam+espesor_arriba, zabajo+diam+espesor_arriba], legendgroup = 'tramo',  marker = dict(color = color_colector_Hex), mode = 'lines', name = 'Tramo', hoverinfo='name')
        tramo_abajo =  go.Scatter(x = [0, xf], y = [zarriba-espesor_abajo, zabajo-espesor_abajo], legendgroup = 'tramo',  marker = dict(color = color_colector_Hex), mode = 'lines', showlegend=False, name = 'Tramo', hoverinfo='name')
        

        #RED ZONE
        lim_red_zone_abajo = go.Scatter(x = [0, xf], y = [y_redzone_1, y_redzone_2], legendgroup = 'redZone', marker = dict(color = '#ff4255'), mode = 'lines', name='Red zone', hovertemplate='Zona no permitida para perforar', hoverinfo = 'name')
        lim_red_zone_arriba = go.Scatter(x = [0, xf], y = [y_redzone_12, y_redzone_22], legendgroup = 'redZone', marker = dict(color = '#ff4255'), mode = 'lines', name='Red zone', showlegend=False, hovertemplate='Zona no permitida para perforar', hoverinfo = 'name')

        #PROPUESTA TUNELERA
        prop_tun_arriba = go.Scatter(x = [0, xf], y = [cota_inicial[0][0] - (profundidad_tunelera + 0.5*diametro_tunelera), cota_final[0][0] - (profundidad_tunelera + 0.5*diametro_tunelera)], legendgroup = 'propTun',  marker = dict(color = 'green'), line = dict(dash = 'dash'), mode = 'lines') 
        prop_tun_Abajo = go.Scatter(x = [0, xf], y = [cota_inicial[0][0] - (profundidad_tunelera - 0.5*diametro_tunelera), cota_final[0][0] - (profundidad_tunelera - 0.5*diametro_tunelera)], legendgroup = 'propTun',  marker = dict(color = 'green'), line = dict(dash = 'dash'), mode = 'lines')
        
        #FILL
        x = [0, xf, xf, 0]
        y = [zarriba+diam+espesor_arriba, zabajo+diam+espesor_arriba, zabajo-espesor_abajo, zarriba-espesor_abajo]
        fill_tramo_area = go.Scatter(x = x, y = y, mode = 'none', legendgroup = 'tramo', fill = 'toself', fillcolor = color_colector_Rgba, showlegend = False, hoverinfo='name')

        y = [zarriba - espesor_abajo, zabajo - espesor_abajo, y_redzone_2, y_redzone_1]
        fill_red_zone_arriba = go.Scatter(x = x, y = y, mode = 'none', legendgroup = 'redZone', fill = 'toself', fillcolor = 'rgba(255, 66, 85, .5)', showlegend = False, hovertemplate='Zona no permitida para perforar', hoverinfo='name', name = 'Red Zone')
        y = [y_redzone_12, y_redzone_22, zabajo + diam + espesor_arriba, zarriba + diam + espesor_arriba]
        fill_red_zone_abajo = go.Scatter(x = x, y = y, mode = 'none', legendgroup = 'redZone', fill = 'toself', fillcolor = 'rgba(255, 66, 85, .5)', showlegend = False, hovertemplate='Zona no permitida para perforar', hoverinfo='name', name = 'Red Zone')
        
        coords_center_tuneleras = [x_dis_esquina,  profundidad_reltaiva]
        puntosAux = go.Scatter(x = [coords_center_tuneleras[0]-diametro_tunelera/2, coords_center_tuneleras[0]+diametro_tunelera/2], y = [coords_center_tuneleras[1]-diametro_tunelera/2, coords_center_tuneleras[1]+diametro_tunelera/2])
        center_tun = go.Scatter(x = [coords_center_tuneleras[0]], y = [coords_center_tuneleras[1]])
        fig = go.Figure( data=([ terreno, tramo_arriba, tramo_abajo, lim_red_zone_abajo, lim_red_zone_arriba, fill_tramo_area, fill_red_zone_arriba, fill_red_zone_abajo]))

        #Dibuja un circulo inscripto en el cuadrado con el vertice inferior izquiero en coords(x0, y0) y el vertice superior derecho (x1, y1)
        if(profundidad_tunelera > 0):
            fig.add_shape(type="circle",
                xref="x",
                yref="y",
                x0 = coords_center_tuneleras[0]-diametro_tunelera/2, y0 = coords_center_tuneleras[1]-diametro_tunelera/2, x1 = coords_center_tuneleras[0]+diametro_tunelera/2, y1 = coords_center_tuneleras[1]+diametro_tunelera/2,
                line_color="black",
                fillcolor="PaleTurquoise",
            )
        min_y = np.min([y_redzone_1, y_redzone_2, y_redzone_12, y_redzone_22])
        line_offset = 1
        #region linea de largo del colector
        fig.add_trace(go.Scatter(
            x = [0, xf/2, xf],
            y = [min_y - line_offset, min_y - line_offset, min_y - line_offset],
            text=['◄',
                str(round(xf, 2)) + 'm',
                '►'],
            mode = "lines+text",
            line = dict(
                color = "black",
                width = 2,
            ),
            textposition = 'top center',
            showlegend = False
        ))  
        #endregion

            
        fig.add_trace(go.Scatter(
            x = [0, xf/2, xf] if(datos[0][6] != 'IMP') else [0, 1, 2], # esto funciono pero no tengo muy claro el porque (por que cambia el texto de los puntos?)
            y = [zarriba, (zarriba+zabajo)/2, zabajo] if(datos[0][6] != 'IMP') else [0, 1, 2],
            mode = 'lines+text+markers',
            text = ['AA', '', 'aa'],
            marker = dict(symbol = "arrow", size = 15, angleref = "previous"),
            line = dict(color = 'blue', width = 2),
            textposition = 'top center',
            showlegend = False
        ))
        #region lineas de distancias a la red zone
        lin_V_offset = 4.5
        y_dis_redZone_1 = cota_inicial[0][0] - (cota_inicial[0][0] - y_redzone_12)
        y_dis_redZone_2 =  cota_final[0][0] - (cota_final[0][0] - y_redzone_22)
        y_dis_redZone_3 = cota_inicial[0][0] - (cota_inicial[0][0] - y_redzone_1)
        y_dis_redZone_4 =  cota_final[0][0] - (cota_final[0][0] - y_redzone_2)
        if(cota_inicial[0][0] - y_redzone_12 > 0):

            fig.add_trace(go.Scatter(
                x = [-lin_V_offset, -lin_V_offset],
                y = [cota_inicial[0][0], y_dis_redZone_1],
                text = ['-', '-'],
                mode = "lines+text",
                line = dict(color = "black", width = 2),
                showlegend = False
            ))  
            fig.add_annotation(text=str(round(cota_inicial[0][0] - y_redzone_12, 2)) + 'm',
                  x = -lin_V_offset - 2, y = (cota_inicial[0][0] + y_dis_redZone_1)/2, showarrow = False,
                  textangle = -90
            )

        if(cota_final[0][0] - y_redzone_22 > 0):
            fig.add_trace(go.Scatter(
                x = [xf + lin_V_offset, xf + lin_V_offset],
                y = [cota_final[0][0], y_dis_redZone_2],
                text=['-', '-'],
                mode = "lines+text",
                line = dict(color = "black", width = 2),
                showlegend = False
            )) 
            fig.add_annotation(text= str(round(cota_final[0][0] - y_redzone_22, 2))+'m',
                  x= xf + lin_V_offset + 2, y=(cota_final[0][0] + y_dis_redZone_2)/2, showarrow=False,
                  textangle = -90
            )
        
        if(cota_inicial[0][0] - y_redzone_1 > 0):
            fig.add_trace(go.Scatter(
                x = [-lin_V_offset*2, -lin_V_offset*2],
                y = [ cota_inicial[0][0], y_dis_redZone_3],
                text=['-', '-'],
                mode = "lines+text",
                line = dict(color = "black", width = 2),
                showlegend = False
            ))
            fig.add_annotation(text= str(round(cota_inicial[0][0] - y_redzone_1, 2))+'m',
                  x= (-lin_V_offset)*2 - 2, y=(cota_inicial[0][0] + y_dis_redZone_3)/2, showarrow=False,
                  textangle = -90
            )  

        if(cota_final[0][0] - y_redzone_2 > 0):
            fig.add_trace(go.Scatter(
                x = [xf + lin_V_offset*2, xf + lin_V_offset*2],
                y = [cota_final[0][0], y_dis_redZone_4],
                text=['-', '-'],
                mode="lines+text",
                line = dict(color = "black", width = 2),
                showlegend = False
            ))  
            fig.add_annotation(text=  str(round(cota_final[0][0] - y_redzone_2, 2))+'m',
                  x=  xf + (lin_V_offset)*2 + 2, y = (cota_final[0][0] + y_dis_redZone_4)/2, showarrow=False,
                  textangle = -90
            )  
        #endregion
        fig.update_layout(scene_xaxis_visible = False, scene_yaxis_visible = False, title = dict(text='Perfil longitudinal', y = .9, x = .5, xanchor='center', yanchor = 'top'), showlegend = True, scene = dict(aspectmode='cube'),  xaxis_title="",
                            yaxis_title="Cota", autosize = True)
        fig['layout']['yaxis'].update(autorange = True)
        return fig

    pendiente_tramo_porcentaje = round((math.fabs(cota_inicial[0][0] - cota_final[0][0]) / xf) * 100, 2)
    datos_to_tabla = [[cota_inicial[0][0], zarriba, datos[0][2], pendiente_tramo_porcentaje, coords_puntos_tapas[2], coords_puntos_tapas[3], cota_inicial[0][1]],
                      [cota_final[0][0], zabajo, datos[0][3], pendiente_tramo_porcentaje, coords_puntos_tapas[0], coords_puntos_tapas[1], cota_final[0][1]],
                      [xf, datos[0][0], datos[0][1]]]

    
    

    return [fig, crear2D(), datos_to_tabla]


################################################
#### PARTE DE DASH FRAMEWORK PARA HACERLO WEB ##
################################################

#region DASH

init_graph = create_graph(1, 0, 0, dis_esquina = 0)

alert1 = dbc.Alert(
    [
        dbc.Row([dbc.Col(html.H4("ERROR", className="alert-heading")),
                 dbc.Col(html.I(className="bi bi-x-octagon-fill me-3")),
                ], justify='around'),
        html.P(
            'Datos faltantes en el servidor para poder dibujar'
        ),
        html.Hr(),
        html.P(
            'Falta dato de cota de aguas arriba',
            className="mb-0",
        ),
    ], 
    color = "danger",
    dismissable = True
)

alert2 = dbc.Alert(
    [
        dbc.Row([ dbc.Col(html.H4("ERROR", className="alert-heading")),
                 dbc.Col(html.I(className="bi bi-x-octagon-fill me-2")),
                ], justify='around'),
        html.P(
            'Datos faltantes en el servidor para poder dibujar'
        ),
        html.Hr(),
        html.P(
            'Falta dato de cota de aguas abajo',
            className="mb-1",
        ),
    ], 
    color="danger",
    dismissable = True
)

alert3 = dbc.Alert(
    [
        dbc.Row([dbc.Col(html.H4("ERROR", className="alert-heading")),
                 dbc.Col(html.I(className="bi bi-x-octagon-fill me-3")),
                ], justify='around'),
        html.P(
            'Datos faltantes en el servidor para poder dibujar'
        ),
        html.Hr(),
        html.P(
            'Faltan dato de cota de aguas abajo y aguas arriba',
            className="mb-2",
        ),
    ], 
    color="danger",
    dismissable = True
)

image_card = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H4("INPUTS", className="card-title"),
                html.H6("Datos de entrada:", className="card-text"),
                html.Hr(),
                html.H6('id de Tramo',className='label'),
                dcc.Input(value = '1', type = 'number', id = 'idT', className='Input'),
                html.H6('Diametro tunelera(m)', className='label'),
                dcc.Input(value = '0', type = 'number', id = 'diametroTun', className='Input'),
                html.H6('Profundidad Tunelera(m)', className='label'),
                dcc.Input(value = '0', type = 'number', id = 'profundidadTun', className='Input'),
                html.H6('distancia a Esquina Aguas Arriba (m)', className='label'),
                dcc.Input(value = '1', type = 'number', id = 'disEsq', className='Input'),
                html.Button('Gnerear grafico', id='button', n_clicks = 0, className='Button'),
                html.Hr(),
                html.Div(id="the_alert", children=[]),
            ], 
        ),
        dbc.CardBody(
            [
                html.H5('COMO USAR'),
                html.P('1-Ingrese todos los datos en la zona de inputs'),
                html.P('2-Clické en el boton de generar grafico'),
                html.P('3-Clicke el boton Play para ver la animacion y resultado de la tunelera'),
                html.Hr(),
                html.H5('Como moverse en la grafica 3D'),
                html.P('🖱 manteniendo click izquierdo y arrastrando roto en el espacio '),
                html.P('🖱 manteniendo click derecho y arrastro para panear '),
                html.P('🔎 con la rueda del raton hago zoom in y zoom out')
            ]
            )
    ],
    color="light",
)

graph_card = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H4("GRAFICAS", className="card-title", style={"text-align": "center"}),
                html.Div([
                dcc.Graph(figure = init_graph[0], id = 'graph3D'),
                dcc.Graph(figure = init_graph[1], id = 'graph2D'),
                dcc.Graph(figure = make_map(csv_data_tramos, 1), id = '_map'),
                dbc.CardBody(
                    [
                        html.H6('DATOS'),
                        html.Div(id = 'tabla', children=[])
                       
                    ], id = 'Tabla')
                ], id = 'Graficos'),

            ]
        ),
    ],
    color="light",
)

# ************************************************************************************************************************************************
app.layout = html.Div([
    dbc.Row([dbc.Col(image_card, width = 2), dbc.Col(graph_card, width = 10)], justify = "around")
], id = 'MainLabel', )
# ************************************************************************************************************************************************

@app.callback(
    [Output('graph3D', 'figure'),
    Output('graph2D', 'figure'),
    Output('tabla', 'children'),
    Output('_map', 'figure'),
    Output('the_alert', 'children'),],
    State('idT', 'value'),
    State('diametroTun', 'value'),
    State('profundidadTun', 'value'),
    State('disEsq', 'value'),
    Input('button', 'n_clicks'),
)
def update_figure(selected_ID, diametro_tunelera, profundidad_tunelera, dis_esquina, n_clicks):
    fig = create_graph(selected_ID, float(diametro_tunelera), float(profundidad_tunelera), float(dis_esquina))
    _map = make_map(csv_data_tramos, selected_ID)
    
    if  (app.server.my_variable != 'Danger!!'):
        fig[0].update_layout(transition_duration = 500)
        fig[1].update_layout(transition_duration = 500)
        _map.update_layout(transition_duration = 500)

    else:
        my_variable = app.server.danger_type
        alert = None
        if(my_variable == 'Danger01'):
            alert = alert1
        elif(my_variable == 'Danger02'):
            alert = alert2
        else:
            alert = alert3
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, alert
    
    datos_tabla = fig[2]
    table_data = pd.DataFrame.from_dict(
        {
            '-': ['Cota de terreno', 'Zampeado', 'Coord X', 'Coord Y', 'id Punto'],
            'AA': [str(datos_tabla[0][0]), str(datos_tabla[0][1]), str(round(datos_tabla[0][4], 2)), str(round(datos_tabla[0][5], 2)), str(datos_tabla[0][6])],
            'aa': [str(datos_tabla[1][0]), str(datos_tabla[1][1]), str(round(datos_tabla[1][4], 2)), str(round(datos_tabla[1][5], 2)), str(datos_tabla[1][6])],
        }
    )
    
    table_data2 = pd.DataFrame.from_dict(
        {
            '-': ['Longitud(m)', 'Tipo tramo', 'Tipo seccion', 'Seccion', 'Pendiente'],
            '--': [str(round(datos_tabla[2][0])), str(datos_tabla[2][1]), str(datos_tabla[2][2]), str(datos_tabla[0][2]), str(datos_tabla[0][3]),]
        }
    )
    
    tabla_res = html.Div(
        [
            dash_table.DataTable(
                data = table_data.to_dict('records'),
                columns = [{'id': x, 'name': x} for x in table_data.columns],
                style_cell={'textAlign': 'center'},
            ),
            dash_table.DataTable(
                data = table_data2.to_dict('records'),
                columns = [{'id': x, 'name': x} for x in table_data2.columns],
                style_cell={'textAlign': 'center'},
            )
        ]
    )

    
    return fig[0], fig[1], tabla_res, _map, None

if __name__ == '__main__':
    app.run_server(debug = False, port='8080')

#endregion

