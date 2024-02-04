import SQC_analysis_tools as sqc
import matplotlib.pyplot as plt
import glob as glob
import os
import argparse
import pandas as pd
import numpy as np
from matplotlib.backends.backend_pdf import PdfPages




color = ['red', 'blue', 'black', 'gold', 'purple', 'green', 'violet', 'peru', 'lightskyblue',
         'pink', 'slategray', 'lime', 'lightgreen', 'cyan', 'brown', 'darkcyan',  'lightgray', 'tan', 'thistle' ]




def IV_analysis(file):
     
     # reads an IVCV file and generates a dataframe with IV data. Should work also for HPK data
     
     if 'HPK' in file:
         start_line = 23
         
     else:
         start_line = 9

     df = sqc.make_Dataframe_IVCV(file, start_line)
     voltage = df['Voltage [V]'].abs()
     current = df['current [A]'].abs()
    
    
     i600 = np.abs(float(df['current [A]'].loc[(df['Voltage [V]'].abs()>599) & (df['Voltage [V]'].abs()<601)]))*1e9
     i800 = np.abs(float(df['current [A]'].loc[(df['Voltage [V]'].abs()>799) & (df['Voltage [V]'].abs()<801)]))*1e9
     
     ratio = i800/i600
    
    
     table_list = [np.round(i600,2), np.round(i800,2), np.round(ratio,2)] 
         
     return voltage, current, table_list


def CV_analysis(file):

    # reads an IVCV file and generates a dataframe with CV data. Should work also for HPK data
     
    if 'HPK' in file:
         start_line = 76
         
    else:
         start_line = 9

    df = sqc.make_Dataframe_IVCV(file, start_line)
    df = df.dropna(subset=['capacitance [F]'])
    voltage = df['Voltage [V]'].abs()
    cap = df['capacitance [F]'].abs()
     
  
    c_inv = 1./cap**2
    
    vfd = sqc.analyse_cv(voltage.values, c_inv.values)
    
    table_list = [np.round(vfd,2)]
  
    return voltage, c_inv, table_list 

 
  
def stripscan_analysis(filename, parameter):

     # reads an Stripscan file and generates a dataframe with all data. Returns only the strip-parameter 

     if '2-S' in filename:
        sensor_id = '2-S'
     else:
        sensor_id = 'PSS'

     df = sqc.make_Dataframe_Stripscan(parameter, filename, sensor_id)

    
     strip = df['Pad']
     parameter = df[parameter]

     return strip, parameter 
  
  

def overlay_plots(files, key, values):

    # itterates over all input files and produces the plots.
    # key-values refer to the dictionary produced from the configuration file
        
    color_index =-1
    flag = True
    list_with_sensors, list_with_value, list_with_medians, list_with_bad_strips = ([] for i in range(4))
    i600_list, i800_list, ratio_list, vfd_list = ([] for i in range(4))
    
    df_with_statistics = pd.DataFrame()
    df_bad_strips = pd.DataFrame()
   
    for file in files:
      
       if not "HPK" in file:
           lbl='-'.join(os.path.basename(file).split('-')[:1 if 'PSS' in file else 2])
           lbl='_'.join(lbl.split('_')[1:])
           lbl=lbl.split('.')[0]
       else:
          lbl='-'.join(os.path.basename(file).split('-')[:1 if 'PSS' in file else 2])
          lbl='_'.join(lbl.split('_')[2:])
          lbl=lbl.split('.')[0] 
    
    
      
       if "IVC" in file or "HPK" in file:
                 
           x,y, table_list = globals()['{}_analysis'.format(key)](file)
           y = y*(float(values['units_conversion']))
           
           if key =='IV':
             
          
             i600_list.append(table_list[0])
             i800_list.append(table_list[1])
             ratio_list.append(table_list[2])
             
           elif key =='CV':
          
             vfd_list.append(table_list[0])
           
           list_with_sensors.append(lbl)
             
            
       elif "Str" in file:  
           
           x, y = stripscan_analysis(file, values['variables'][1])
           y = y*(float(values['units_conversion']))
           
           bad_strips = sqc.find_bad_strips(y, key, values, lbl)
              
           median, MAD = sqc.find_median_MAD(y)
       
       
      
           list_with_value.append('{:.2f} \u00B1 {:.2f}'.format(np.round(median, 2), np.round(MAD,2)))
           list_with_medians.append(median)
           list_with_bad_strips.append(bad_strips)
           list_with_sensors.append(lbl)
         
       
      
       
       color_index +=1

       sqc.plot_graph(abs(x), abs(y), color[color_index], lbl, values['title'], values['variables'][0] + ' ' , values['variables'][1] + ' ' +'[{}]'.format(values['units']))
        
       
       if (y.abs()).max() > (50*y.abs()).median() and "Str" in file:
         
          plt.yscale('log')
   
    if key in ['IV']:

       list_with_sensors.append('Batch Mean')
       i600_list.append(np.round(np.mean(i600_list),2))
       i800_list.append(np.round(np.mean(i800_list),2))
       ratio_list.append(np.round(np.mean(ratio_list),2))

       df_with_statistics['Sensor'] = list_with_sensors
       df_with_statistics['I600'] = i600_list
       df_with_statistics['I800'] = i800_list
       df_with_statistics['Ratio'] = ratio_list
       
       
    elif key in ['CV']:
       vfd_list.append(np.round(np.mean(vfd_list),2))
       list_with_sensors.append('Batch Mean')
       df_with_statistics['Sensor'] = list_with_sensors
       df_with_statistics['VFD'] = vfd_list
       
       
       
   
    if key not in ['IV', 'CV'] and len(list_with_medians)>1:
    
       average_parameter = np.mean(list_with_medians)
       std_parameter = np.std(list_with_medians)   

       df_bad_strips['Sensor'] = list_with_sensors
       df_bad_strips[key] = list_with_bad_strips        
     
       list_with_sensors.append('Batch Mean')
       list_with_value.append('{:.2f} \u00B1 {:.2f}'.format(np.round(average_parameter,2), np.round(std_parameter,2)))
       df_with_statistics['Sensor'] = list_with_sensors
       df_with_statistics[key] = list_with_value
       
       


    
    return df_with_statistics, df_bad_strips
    
    
    
       
     
def find_most_recent_file(files):

   # in case of remeasurements, it returns the file of the latest date

   df = pd.DataFrame()
   df['File'] = files
   
   df['Sensor'] = ['-'.join(os.path.basename(file).split('-')[:1 if 'PSS' in file else 2]) for file in files]
   df['Date'] = ['-'.join(os.path.basename(f).split('-')[-5:]).split('.')[0] for f in files]
   
   df = df.sort_values('Date').drop_duplicates('Sensor',keep='last')
   
   most_recent_files = [f for f in files if f in df['File'].values]
   
   return most_recent_files



def make_pdf_with_plots(files, measurement_config, pdf_name):

  # produces the pdfs with the plots
  parameter_df = pd.DataFrame()
  df_with_bad_strips = pd.DataFrame()
  
  
  with PdfPages('{}.pdf'.format(pdf_name)) as pdf:
      for key,values in measurement_config.items():
         
         scale_factor = values['units_conversion'] # to scale the parameter to the typical order of magnitude
         
         fig = plt.figure()
         df, df_bad = overlay_plots(files, key, values)
         
        
         if key == 'IV':
            parameter_df = df.copy()
         elif key == 'CV':
            parameter_df = parameter_df.join(df['VFD'])
           
         elif key =='Istrip':
            parameter_df = df.copy()
            df_with_bad_strips = df_bad.copy()

         else:
           if key not in ['Idark', 'Temperature', 'Humidity']:
             parameter_df = parameter_df.join(df[key])
             df_with_bad_strips = df_with_bad_strips.join(df_bad[key])
             
         pdf.savefig(fig)
  
  return parameter_df ,  df_with_bad_strips 
    
  
  
def build_slack_message(dictionary, sensor):

   # build the message to send to slack channel!
    
   main_message = 'SQC measurement of sensor {} is done!'.format(sensor)
   additional_message = ''
   
   for key, value in dictionary.items():
        if not value:
            additional_message = 'The {} measurement had at least one outlier, please check the plot'.format(key)
            main_message = main_message + "\n" + additional_message
        
   return main_message
    
    
    

def parse_args():

    parser = argparse.ArgumentParser(epilog = 'a path to directory containing ascii files to be analysed')
    parser.add_argument('path')
   # parser.add_argument('sensor')
    return parser.parse_args()




def main():


    args = parse_args()
    iv_df = pd.DataFrame()
    stripscan_df = pd.DataFrame()
    
    filename = glob.glob(f'{args.path}/*/*.txt', recursive=True) 
    #adapted for SQC data as stored on HEROS
 
    if len(filename)<1:
       filename = glob.glob(f'{args.path}/*.txt', recursive=True) 
       # assuming that you have HPK ascii files all stored in one folder
       
       
    most_recent_files = find_most_recent_file(filename)
    
  
    IVCV_files = [f for f in most_recent_files if "IVC" in f]
    Stripscan_files = [f for f in most_recent_files if "Str" in f]
    HPK_files = [f for f in filename if "HPK" in f]
   
    
    IV_config = sqc.read_config()['IVCV_Parameters']
  
    Stripscan_config = sqc.read_config()['Strip_Parameters']
    
    HPK_config = sqc.read_config()['Strip_Parameters']
    
    if len(IVCV_files)>=1:
         iv_df, df_with_bad_strips = make_pdf_with_plots(IVCV_files, IV_config, "IVCV")
       
    if len(Stripscan_files)>=1:
        stripscan_df, df_with_bad_strips = make_pdf_with_plots(Stripscan_files, Stripscan_config, "Stripscan")
    
      
    
    if len(HPK_files)>=1:
         make_pdf_with_plots(HPK_files, IV_config, "HPK_IVCV")
    
    
    if iv_df.shape[0]>1 and stripscan_df.shape[0]>1:
    
       sqc.make_html_table(iv_df, stripscan_df, df_with_bad_strips)
    
    #message = build_slack_message(dictionary_with_flags, args.sensor)
   # sqc.send_slack_message(message)
    
   


if __name__ == "__main__":
    main()