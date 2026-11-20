import logging
from typing import List, Union
from concurrent.futures import ProcessPoolExecutor
from io import BytesIO
from PIL import Image
from tqdm import tqdm
import time

import plotly.graph_objects as go
from PIL import Image
import plotly.offline as po
from typing import Optional
logger = logging.getLogger(__name__)
from ..constants import (
    DOSEMAP_COLORSCALE,
    PHANTOM_MODEL_PLANE,
    PLOT_EYE_BACK,
    PLOT_EYE_FRONT,
    PLOT_EYE_LEFT,
    PLOT_EYE_RIGHT,
    PLOT_FONT_FAMILY,
    PLOT_ORDER_STATIC,
)

from plotly.io import to_image
import imageio.v2 as imageio
import copy
import plotly.io as pio
kaleido_scope=pio.kaleido.scope


def render_frame(fig):
    img_bytes = kaleido_scope.transform(fig, format="png",width=800, height=600, scale=1.)
    img = Image.open(BytesIO(img_bytes)).convert("RGB")
    return img

def create_plot_and_save_to_file(mode: str, data: List[Union[go.Mesh3d, go.Scatter3d]], layout: go.Layout, nome : Optional[str] = ""):
    
    """
    :param mode:
    :param data:
    :param layout:
    :return:
    
    """
      
   
    #voglio che faccia anche la figura e basta    
    plot_filename = f"{mode}.html"
    logger.debug(f"Creating plot and savint to file {plot_filename}")
    

    fig=go.Figure(data=data, layout=layout)
    #fig.write_html("prova.html")
   
    gif_name=nome+".gif"
    print(gif_name)
  
    width=800
    height=600
    duration=1000

    steps = fig.layout.sliders[0].steps
   
    images = []
    a=int(len(fig.data)/10)
    fig.update_layout(showlegend=False, hovermode=False, annotations=[],title=None)
    figs=[]
    for i, step in enumerate(tqdm(steps, desc="Generazione GIF")):
        # Copia intera della figura
        for k in range(len(fig.data)):
            fig.data[k].visible=False
        for j in range(10):        
            fig.data[a*j+i].visible=True

        fig.layout.sliders[0].update(active=i)    
        visible_traces=[t for t in fig.data if t.visible is not False] 
        f = go.Figure(data=visible_traces, layout=fig.layout)
        figs.append(f)

    with ProcessPoolExecutor() as executor:
        futures = [executor.submit(render_frame,fig) for fig in figs]
        images=[]
        #img_bytes = to_image(fig, format="png", width=width, height=height, scale=1.)
        #    img_bytes = kaleido_scope.transform(fig, format="png",width=width, height=height, scale=1.)
        
        #img = Image.open(BytesIO(img_bytes)).convert("RGB")
        #img = img.resize((800, 600), resample=Image.BOX)
        for f in tqdm(futures, desc="Rendering frames"):
            images.append(f.result())
        
        

    # Salva GIF
    imageio.mimsave(gif_name, images, duration=duration)
    print(f"✅ GIF salvata come {gif_name}")
    
    
   # except:
   #     print('non so perché dà errore')
   #     continue
    
    
    """
    fig.update_layout(scene_camera=dict(
    eye=dict(x=1.5, y=-1.5, z=1.5)  # z alto per altezza, x e y spostati per inclinazione
    ))
    """    
   
    
    """
    po.plot(fig, filename=plot_filename)
    
       
    #fig.show()
    
    fig = go.Figure(data=data, layout=layout)
    """ 

    #fig.write_image(f"images\\"+nome+".png", height=300, width=400, scale=0.5)
    #im = Image.open(f"images\\"+nome+"_p.png")
    #im.show()
    
    
   
