# -*- coding: utf-8 -*-
"""
Created on Thu Feb 27 15:38:47 2025

@author: balboni.erica
"""

"""
Iacomino + Balboni
"""

import pandas as pd
from pyskindose.main import  _parse_settings_to_settings_class
from pyskindose.analyze_data import analyze_data
import csv
from numpy import array, shape, repeat, sign
from tkinter import filedialog
import plotly.io as pio
pio.renderers.default = "browser"
import pydicom
import json

"""
RDSR IMPORT
"""
files=[filedialog.askopenfilename()][0]
folder=''

def estrai_content(ContentSequence):
        for xray_event_content in ContentSequence:
                tag = (
                xray_event_content.ConceptNameCodeSequence[0]
                .CodeMeaning.replace(" ", "")
                .replace("-", "")
                .replace("(", "")
                .replace(")", "")
                .replace(".", "")
                )
                if tag in data_parsed_dict.keys():
                    tag = "_".join([tag, "1"])
                
                
                if 'ConceptCodeSequence' in xray_event_content:
                    data_parsed_dict[tag] = xray_event_content.ConceptCodeSequence[0].CodeMeaning
                
                elif 'MeasuredValueSequence' in xray_event_content:
                    unit = (
                        xray_event_content.MeasuredValueSequence[0]
                        .MeasurementUnitsCodeSequence[0]
                        .CodeValue.replace(".", "")
                    )
    
                    tag = "_".join([tag, unit])
                    if tag in data_parsed_dict.keys():
                        tag = "_".join([tag, "1"])
                    data_parsed_dict[tag] = xray_event_content.MeasuredValueSequence[0].NumericValue
                elif 'TextValue' in xray_event_content:
                   data_parsed_dict[tag] = xray_event_content.TextValue 
                
                elif 'UID' in xray_event_content:
                    data_parsed_dict[tag] = xray_event_content.UID
               
                if 'ContentSequence' in xray_event_content:
                    estrai_content(xray_event_content.ContentSequence)
                
                elif 'DateTime' in xray_event_content :
                    data_parsed_dict[tag] =xray_event_content.DateTime
                
                
            
data_raw = pydicom.dcmread(files)
prodcedure_dicts = []    
for rdsr_content in data_raw.ContentSequence:
    if rdsr_content.ConceptNameCodeSequence[0].CodeMeaning == 'Irradiation Event X-Ray Data':
        data_parsed_dict = dict()
        for dicoms in dir(data_raw):
            try :
                if isinstance(getattr(data_raw, dicoms),str):
                    if "__" not in dicoms :                    
                        data_parsed_dict[dicoms] = getattr(data_raw, dicoms)
            except :
                continue
        
        estrai_content(rdsr_content.ContentSequence)
        prodcedure_dicts.append(data_parsed_dict)

data_parsed = pd.DataFrame(prodcedure_dicts)    
data_parsed.to_excel(files+'.xlsx')  



data_total = data_parsed

"""
IMPORT SETTINGS
"""
settings =_parse_settings_to_settings_class(settings="/opt/pyenv/versions/PyskindoseEnv/lib/python3.8/site-packages/pyskindose/settings_example.json")

    

with open('/srv/data/diagnostica/Pyskindose/DOSI_PSD.csv', mode='a', newline='') as csv_file:
    """
    RESULTS FILE
    """
    nomicolonne= ['STUDY', 'MODEL', 'PSD', 'KIRP', 'DATE','PID']
    writer = csv.DictWriter(csv_file, fieldnames=nomicolonne, delimiter=";")
    writer.writeheader()
    studi = data_total['StudyID'].unique()
           
    for i in studi :           
        """
        RENAME VARIABLES AND FILL ZEROS
        """
        
        data = data_total[data_total['StudyID'] == i]                 
        
        data = data.reset_index()
        data.fillna(0, inplace=True)
        if "ManufacturerModelName" in data.columns:
            data.rename(columns={"ManufacturerModelName": "model"}, inplace=True)
        else:
            data.rename(columns={"StationName": "model"}, inplace=True)
        if not "DeviceModelName" in data.columns:
            data.insert(1,"DeviceModelName","a")
        data.rename(columns={"DistanceSourcetoDetector_mm": "DSD"}, inplace=True)
        dist = sorted(data['DSD'].unique())
        for i in range(len(data)):
            if data['DSD'][i] == 0:
                data['DSD'][i] = dist[1]
        data.rename(columns={"DistanceSourcetoIsocenter_mm": "DSI"}, inplace=True)
        data.rename(columns={"PulseWidth_ms": "DID"}, inplace=True)
        data['DID'] = data['DSD'] - data['DSI']
        
        if "DistanceSourcetoReferencePoint_mm" in data.columns:
            data.rename(columns={"DistanceSourcetoReferencePoint_mm": "DSIRP"}, inplace=True)
            for i in range(len(data)):
                if data['DSIRP'][i] == 0:
                        data['DSIRP'][i] = data['DistanceSourcetoReferencePoint_mm.1'][i]
        else:
            data.insert(1,'DSIRP',0)
            for i in range(len(data)):
                if data['DSIRP'][i] == 0:
                    data['DSIRP'][i] = data['DSI'][i] - 15
        
                
        if not "PositionerPrimaryEndAngle_deg" in data.columns:
            data.insert(1,'PositionerPrimaryEndAngle_deg',0)
        if not "PositionerSecondaryEndAngle_deg" in data.columns:
            data.insert(1,'PositionerSecondaryEndAngle_deg',0)
            
        if data['model'][0] == 'Azurion':
            data['model'] = 'Azurion 7 M20'
            
        
        with open("normalization_settings.json", "r", encoding="utf-8") as norm_file:
            normalization_settings=json.load(norm_file)
        for setting in normalization_settings["normalization_settings"]:
        
            if not (
                data['Manufacturer'][0] == setting['manufacturer']
                and data['model'][0] in setting['models']
            ):
                continue        
            trans_offset = setting["translation_offset"]        
            trans_dir = {k: (1 if v == "+" else -1) for k, v in setting["translation_direction"].items()}        
            rot_dir = {k: (1 if v == "+" else -1) for k, v in setting["rotation_direction"].items()}          
            field_size_mode = setting["field_size_mode"]
            detector_side_length = setting["detector_side_length"]    
        
        """
        CBCT
        """
        num_rot=shape(data[data["IrradiationEventType"]=="Rotational Acquisition"])[0]
        div_ang=10
            
        if num_rot!=0:
            data_rot=data[data["IrradiationEventType"]=="Rotational Acquisition"]
            lista=list(data_rot.index.values)
            for i in lista:
                if  data_rot['PositionerPrimaryEndAngle_deg'][i]!=0 :
                    num_beams_s=(data['PositionerPrimaryEndAngle_deg'][i]-
                                 data['PositionerPrimaryAngle_deg'][i])
                    num_beams=num_beams_s+180*(1-sign(num_beams_s))        
                    data_rot['DoseAreaProduct_Gym2'][i]=data_rot['DoseAreaProduct_Gym2'][i]*div_ang/abs(num_beams)
                    data_rot['DoseRP_Gy'][i]=data_rot['DoseRP_Gy'][i]*div_ang/abs(num_beams)  
                    data_rot=data_rot.append(data_rot.loc[repeat(i,abs(int(num_beams/div_ang)-1))])                                                       
                    data_rot['PositionerPrimaryAngle_deg'].loc[i]=data_rot['PositionerPrimaryAngle_deg'].loc[
                    i]-div_ang*sign(num_beams_s)*array(range(abs(int(int(num_beams/div_ang))))) 
                        
                elif  data_rot['PositionerSecondaryEndAngle_deg'][i]!=0 :
                    num_beams_s=(data['PositionerSecondaryEndAngle_deg'][i]-
                                 data['PositionerSecondaryAngle_deg'][i])
                    num_beams=num_beams_s+180*(1-sign(num_beams_s)) #EB: mi serve perché devo aggiungere 360 solo se ho segno meno, se no non aggiungo niente       
                    data_rot['DoseAreaProduct_Gym2'][i]=data_rot['DoseAreaProduct_Gym2'][i]*div_ang/abs(num_beams)
                    data_rot['DoseRP_Gy'][i]=data_rot['DoseRP_Gy'][i]*div_ang/abs(num_beams)  
                    data_rot=data_rot.append(data_rot.loc[repeat(i,abs(int(num_beams/div_ang)-1))])                                                       
                    data_rot['PositionerSecondaryAngle_deg'].loc[i]=data_rot['PositionerSecondaryAngle_deg'].loc[
                    i]+sign(num_beams_s)*array(range(abs(int(int(num_beams/div_ang)))))  
                    data_rot=data_rot.append(data_rot.loc[repeat(i,abs(num_beams/div_ang-1))])                                                       
                    data_rot['PositionerSecondaryAngle_deg'].loc[i]=data_rot['PositionerSecondaryAngle_deg'].loc[
                    i]+div_ang*sign(num_beams_s)*array(range(abs(int(num_beams/div_ang))))    
                    
            data_flu=data[data["IrradiationEventType"]!="Rotational Acquisition"]        
            data=data_flu.append(data_rot, ignore_index=True)
        
        if shape(data)[0]>2000:
            print("Too many lines! Change something")
            writer.writerow({'STUDY': data['AccessionNumber'][0],'MODEL': data['model'][0],'PSD' : "Too many lines!",  
                             'KIRP' : array(data["DoseRP_Gy"]).sum(), 'DATE': array(data['DateTimeStarted'])[0]})
            continue
           
        data_ssd=data.copy()
        data_ssd=data_ssd.sort_values(by=["DateTimeStarted","PositionerPrimaryAngle_deg"])
        """
        MORE VARIABLE RENAME
        """
        
        
        data.rename(columns={"NumberofFrames_1": "DSL"}, inplace=True)
        data['DSL'] = 50            
        data.rename(columns={"IrradiationEventType": "acquisition_type"}, inplace=True)
        data.rename(columns={"AcquisitionPlane": "acquisition_plane"}, inplace=True)
        #y - VERTICAL ()
        #X - LONGITUDINAL
        #Z - LATERAL
        data.rename(columns={"TableHeightPosition_mm": "Ty"}, inplace=True)
        data.rename(columns={"TableLongitudinalPosition_mm": "Tx"}, inplace=True)
        data.rename(columns={"TableLateralPosition_mm": "Tz"}, inplace=True)
        data.rename(columns={"PositionerPrimaryAngle_deg": "Ap1"}, inplace=True)
        data.rename(columns={"PositionerSecondaryAngle_deg": "Ap2"}, inplace=True)
        data.rename(columns={"TableHorizontalRotationAngle_deg": "Ap3"}, inplace=True)    
        
        
        data.rename(columns={"TableHeadTiltAngle_deg": "At1"}, inplace=True)
        data.rename(columns={"TableCradleTiltAngle_deg": "At2"}, inplace=True)
        data.rename(columns={"TableHorizontalRotationAngle_deg": "At3"}, inplace=True)
        data['At3']=0
        if not "XRayFilterThicknessMaximum_mm" in data.columns:
            data.insert(1,"XRayFilterThicknessMaximum_mm",0)
            data.insert(1,"XRayFilterThicknessMaximum_mm_1",0)
            data.XRayFilterThicknessMaximum_mm=data.XRayFilterThicknessMinimum_mm
            data.XRayFilterThicknessMaximum_mm_1=data.XRayFilterThicknessMinimum_mm_1
                    
        data["filter_thickness_Cu"]=0
        data["filter_thickness_Al"]=0
        for i in range(len(data)):
           if  data['XRayFilterMaterial'][i]==0:
               continue
           elif "Copper" in data['XRayFilterMaterial'][i]:
               data["filter_thickness_Cu"][i]=data["XRayFilterThicknessMaximum_mm"][i]
           elif "Aluminum" in data['XRayFilterMaterial'][i]:    
               data["filter_thickness_Al"][i]=data["XRayFilterThicknessMaximum_mm"][i]
           if 'XRayFilterMaterial_1' in data.columns:
               if "Copper" in data['XRayFilterMaterial_1'][i]:
                   data["filter_thickness_Cu"][i]=data["XRayFilterThicknessMaximum_mm_1"][i]
               elif "Aluminum" in data['XRayFilterMaterial_1'][i]:
                   data["filter_thickness_Al"][i]=data["XRayFilterThicknessMaximum_mm_1"][i]
                           
               
        if data["acquisition_plane"][0]=="Single Plane":
            data["acquisition_plane"]="Plane A"
        
        """
        COORDINATE NORMALIZATION
        """
               
          
        
        #OFFSET
        for i in range(len(data)):
            data['DSI'][i]=data['DSI'][i]/10
            data['DID'][i]=data['DID'][i]/10
            data['DSIRP'][i]=data['DSIRP'][i]/10
            data['DSD'][i]=data['DSD'][i]/10
            data['Tz'][i]= trans_dir['z']*((data['Tz'][i])/10 - trans_offset['z'])
            data['Tx'][i]= trans_dir['x']*((data['Tx'][i])/10 -trans_offset['x'] )         
            data['Ty'][i]=trans_dir['y']*((data['Ty'][i])/10-trans_offset['y'])
            data['Ap1'][i]= rot_dir['Ap1']*data['Ap1'][i]
            data['Ap2'][i]= rot_dir['Ap2']*data['Ap2'][i]
            data['Ap3'][i]= rot_dir['Ap3']*data['Ap3'][i]
                                    
                
            
        
        data.rename(columns={"KVP_kV": "kVp"}, inplace=True)
        for i in range(len(data)):
            if data['kVp'][i] == 0:
                data['kVp'][i] = data['kVp'][i-1]
        data.rename(columns={"CollimatedFieldHeight_mm": "FS_long"}, inplace=True)
        data.rename(columns={"CollimatedFieldWidth_mm": "FS_lat"}, inplace=True)
        if 'FS_long' in data.columns:
            data['FS_long'] = data['FS_long']/10
            data['FS_lat'] = data['FS_lat']/10
            
        else:
            data.insert(1,'FS_long',0)
            data.insert(1,'FS_lat',0)
        data.rename(columns={"DoseRP_Gy": "K_IRP"}, inplace=True)
        for i in range(len(data)):
            if data['FS_long'][i]==0 or data['FS_lat'][i]==0:
                A_IRP = data['DoseAreaProduct_Gym2'][i]/ data['K_IRP'][i]
                data['DSIRP'][i] = data['DSI'][i] - 15
                data['FS_long'][i]= 100*((A_IRP**(1/2)) * data['DSD'][i]/data['DSIRP'][i])
                data['FS_lat'][i]=data['FS_long'][i]
            
                
        model = data.model[0]
        
        nome = "/srv/data/diagnostica/Pyskindose/IMMAGINI/"+str(data['PatientID'][0])

        
        """
        PATIENT POSITION
        """
        
        if (data['PatientSex'][0] == 'F'):
            data['PatientSex'][0] = 'FEMALE'
        
               
        if (data['PatientSex'][0] == 'FEMALE'):
            settings.phantom.human_mesh="AF" 
        if (data['PatientOrientationModifier'][0] == 'prone') and (data['PatientTableRelationship'][0] == 'headfirst'):
            data['Ap2'][i]= -rot_dir['Ap2']*data['Ap2'][i]            
            data['Ap1'] = 180+data['Ap1']
            settings.phantom.human_mesh="AM_prono"
            if (data['PatientSex'][0] == 'FEMALE'):
                settings.phantom.human_mesh="AF_prono"            
        elif (data['PatientOrientationModifier'][0] == 'prone') and (data['PatientTableRelationship'][0] == 'feetfirst'):
            settings.phantom.human_mesh="AM_prono_FF"  
            data['Ap1'] = rot_dir['Ap2']*(180+data['Ap1'])
            if (data['PatientSex'][0] == 'FEMALE'):
                settings.phantom.human_mesh="AF_prono_FF" 
            data['Ap2'][i]= -rot_dir['Ap2']*data['Ap2'][i] 
                
                
        elif (data['PatientOrientationModifier'][0] == 'supine') and (data['PatientTableRelationship'][0] == 'feetfirst'):
            settings.phantom.human_mesh="AM_supino_FF"
            data['Ap2'] = -data['Ap2']
            data['Ap1'] = -data['Ap1']
            if (data['PatientSex'][0] == 'FEMALE'):
                settings.phantom.human_mesh="AF_supino_FF"
            
        elif (data['PatientOrientationModifier'][0] == 'left lateral decubitus') :
            settings.phantom.human_mesh="AM_decubito_sx"  
            data['Ap1'] = data['Ap1']+90
            if (data['PatientSex'][0] == 'FEMALE'):
                settings.phantom.human_mesh="AF_decubito_sx"
        elif (data['PatientOrientationModifier'][0] == 'right lateral decubitus') :
            settings.phantom.human_mesh="AM_decubito_dx"  
            data['Ap1'] = data['Ap1']-90
            if (data['PatientSex'][0] == 'FEMALE'):
                settings.phantom.human_mesh="AF_decubito_dx" 
        
        
        
        data=data.sort_values(by=["DateTimeStarted","Ap1"])
        data=data.reset_index()

        data.DeviceModelName=model
        data.DoseAreaProduct_Gym2=data.DoseAreaProduct_Gym2*1000
        data.K_IRP=data.K_IRP*1000
        data.to_excel(files+'_normalized.xlsx') 
        
        
        """
        #ONLY FILMS
        settings.phantom.model="plane"
        settings.phantom.patient_offset.d_lat=-10
        settings.phantom.dimension.pad_length=40
        settings.phantom.dimension.pad_width=30
        settings.phantom.dimension.pad_thickness=20
        """          
        
        settings.mode="calculate_dose"
        settings.plot.plot_dosemap=True                 
        settings.plot.interactivity=False
        settings.plot.notebook_mode=False
        output = analyze_data(normalized_data = data, settings=settings, nome = nome)
        psd = str(max(output[0]['dose_map']))                
        writer.writerow({'STUDY': data['AccessionNumber'][0],'MODEL': data['model'][0],'PSD' : str(psd).replace('.',','), 
                         'KIRP' : str(array(data["K_IRP"]).sum()).replace('.',','), 'DATE': array(data['DateTimeStarted'])[0],
                         'PID': array(data['PatientID'])[0]})
        settings1=settings
        
        
        settings1.mode="plot_procedure"  
        settings1.plot.plot_dosemap=False
        analyze_data(normalized_data=data, settings=settings1, nome=nome)
        
       
        
   
           
        
       
        
       
        
       
        
       
        
