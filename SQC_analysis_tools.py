import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from scipy.interpolate import CubicSpline
import warnings
from statistics import mean, stdev, median
import glob
import yaml
import traceback
from scipy.stats import linregress
import scipy.signal
import requests
import sys
import getopt
from pretty_html_table import build_table
from matplotlib.backends.backend_pdf import PdfPages




def read_config():
    with open('SQC_parameters.yml', 'r') as f:
        conf = yaml.load(f, Loader=yaml.FullLoader)

    return conf
    
    
    
def get_link_for_slack_api():

    with open('slack_link.txt') as f:
        link = f.readlines()
        
    f.close()
    
    return str(link[0])




def convert_txt_to_df(filename, headers, skip):

    if 'HPK_' in filename:
        dat = np.genfromtxt(filename, skip_header=skip, max_rows=51)

    else:

        dat = np.genfromtxt(filename, skip_header= skip)

    df = pd.DataFrame(dat, columns = headers)

    return df




def make_Dataframe_Stripscan(parameter, filename, sensor_id):


    headers_Stripscan = read_config()['headers']['Str']
    
    df= convert_txt_to_df(filename, headers_Stripscan, 23 if sensor_id=='2-S' else 16) 
    df[parameter] = pd.to_numeric(df[parameter])
    df = df.dropna(subset=[parameter])

    return df



def make_Dataframe_IVCV(filename, start_line):

    
    if 'IVC' in filename: # if SQC IV data
        headers_IVC = read_config()['headers']['IVCV']
    elif 'HPK' in filename: # if HPK IV data
        if start_line==23:
          headers_IVC = read_config()['headers']['HPK_IV'] # condition true if HPK IV 
        else:
          headers_IVC = read_config()['headers']['HPK_CV'] # condition true if HPK CV
          
    df = convert_txt_to_df(filename, headers_IVC, start_line) 
    

    return df
   



def plot_graph(x, y, color, label, title, xlab, ylab):

     
     plt.plot(x, y, '-o', color=color, markersize=4, label =label)
     #plt.title(title, fontname="Times New Roman", fontsize=16, fontweight='bold')
     plt.xlabel(xlab, fontsize=13, fontweight='bold')
     plt.ylabel(ylab, fontsize=13, fontweight='bold')
   
     plt.tick_params(axis = 'y', labelsize=12)
     plt.tick_params(axis='x', labelsize=12)
 
     if 'IV' in title and np.max(y)>1000:
           plt.ylim(0, 1000) # limit current at 1 uA in order to be comparable to HPK plot 
    
   
     plt.legend(loc='best', fontsize=8, ncol=1)
     plt.tight_layout()



def find_median_MAD(parameter):

    median = parameter.median()
    
    diff = (parameter - median).abs()
    MAD = diff.median()
  
    
    return median, MAD


def analyse_cv( v, c, area=1.56e-4, carrier='electrons', cut_param=0.008, max_v=500, savgol_windowsize=None, min_correl=0.1, debug=False):
    """
    Diode CV: Extract depletion voltage and resistivity.
    Parameters:
    v ... voltage
    c ... capacitance
    area ... implant size in [m^2] - defaults to quarter
    carrier ... majority charge carriers ['holes', 'electrons']
    cut_param ... used to cut on 1st derivative to id voltage regions
    max_v ... for definition of fit region, only consider voltages < max_v
    savgol_windowsize ... number of points to calculate the derivative, needs to be odd
    min_correl ... minimum correlation coefficient to say that it worked
    Returns:
    v_dep1 ... full depletion voltage via inflection
    v_dep2 ... full depletion voltage via intersection
    rho ... resistivity
    conc ... bulk doping concentration
    """

    # init
    v_dep1 = v_dep2 = rho = conc = np.nan
    a_rise = b_rise = a_const = b_const = np.nan
    v_rise = []
    v_const = []
    status = 'Pass'

    if savgol_windowsize is None:
        # savgol_windowsize = int(len(c) / 40 + 1) * 2 + 1  # a suitable off windowsie - making 20 windows along the whole measurement
        savgol_windowsize = int(len(c) / 30 + 1) * 2 + 1  # a suitable off windowsie - making 15 windows along the whole measurement
        # the window size needs to be an odd number, therefore this strange calculation

    # invert and square
    #c = [1./i**2 for i in c]
  
    # get spline fit, requires strictlty increasing array
    y_norm = c / np.max(c)
    x_norm = np.arange(len(y_norm))
   
    spl_dev = scipy.signal.savgol_filter(y_norm, window_length=savgol_windowsize, polyorder=1, deriv=1)

    # for definition of fit region, only consider voltages < max_v
    idv_max = max([i for i, a in enumerate(v) if abs(a) < max_v])
    spl_dev = spl_dev[:idv_max]

    idx_rise = []
    idx_const = []

    with warnings.catch_warnings():
        warnings.filterwarnings('error')

        try:
            # get regions for indexing
            idx_rise = [i for i in range(2, len(spl_dev-1)) if ((spl_dev[i]) > cut_param)]  # the first and last value seems to be off sometimes
            idx_const = [i for i in range(2, len(spl_dev-1)) if ((spl_dev[i]) < cut_param) and i > idx_rise[-1]]

            v_rise = v[idx_rise[0]:idx_rise[-1] + 1]
            v_const = v[idx_const[0]:idx_const[-1] + 1]
            c_rise = c[idx_rise[0]:idx_rise[-1] + 1]
            c_const = c[idx_const[0]:idx_const[-1] + 1]

            # line fits to each region
            a_rise, b_rise, r_value_rise, p_value_rise, std_err_rise = scipy.stats.linregress(v_rise, c_rise)
            a_const, b_const, r_value_const, p_value_const, std_err_const = scipy.stats.linregress(v_const, c_const)

        
            mu = 1350*1e-4 

            # full depletion voltage via max. 1st derivative
            v_dep1 = v[np.argmax(spl_dev)]

            # full depletion via intersection
            v_dep2 = (b_const - b_rise) / (a_rise - a_const)
            
            conc = 2. / (1.6e-19 * 11.68 *8.854e-12 * a_rise * area**2) 
            rho = 1. / (mu*1.6e-19 *conc)



        except np.RankWarning:
            
            print("The array has too few data points. Try changing the cut_param parameter.")

        except (ValueError, TypeError, IndexError):
        
            print("The array seems empty. Try changing the cut_param parameter.")

        if status == 'Fail':
            #print("The fit didn't work as expected, returning nan")
            return np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, np.nan, STATUS_FAILED
    
    return v_dep1


def make_html_table(df_iv, df_stripscan, df_with_bad_strips):

   

   batch = '_'.join(df_iv['Sensor'][0].split('_')[0:1])
   print(batch)   
   html_table_blue_light = build_table(df_iv, 'blue_light', text_align='center')
   html_table_blue_light_2 = build_table(df_stripscan, 'blue_light', text_align='center')
   html_table_blue_light_3 = build_table(df_with_bad_strips, 'blue_light', text_align='center')

   with open('sqc_tables_batch_{}.html'.format(batch), 'w', encoding="utf-8") as f:
       f.write("<html><body> <h1>SQC Parameters Batch <font color = #4000ff>{}</font></h1>\n</body></html>".format(batch))
       f.write("\n")
       f.write(html_table_blue_light + "\n" + html_table_blue_light_2 +"\n" + html_table_blue_light_3)




def find_bad_strips(data, parameter, config, sensor):

   bad_strips = 0
   if '2-S' in sensor:
   
      string ='2S_threshold'
   elif 'PSS' in sensor:
   
      string  = 'PSS_threshold'
      
   
   for i in data:
      if parameter in ['Istrip', 'Idiel', 'Cint']:
         if np.abs(i) > config[string]:
             bad_strips +=1
             
      elif parameter in ['Cac', 'Rint']:
           if np.abs(i) < config[string]:
             bad_strips +=1
      elif parameter=='Rpoly':
         
          if i< (config[string] - 0.5) or i> (config[string] + 0.5):
              bad_strips +=1
           
   return bad_strips
   
   
def evaluate_results(y, config_file, parameter_name, sensor_type):

    flag = True
    for i in y:
       if sensor_type=='2-S' and parameter_name=='Cac':
           i = i/2 # to scale at same strip length with PSS and facilitate the comparison
           
       if i< float(config_file['expected_range'][0]) or i > float(config_file['expected_range'][1]):
           
           flag = False
           
    return flag




def send_slack_message(message):

    link_from_slack = get_link_for_slack_api() 
    
    payload = '{"text": "%s"}' %message
    response = requests.post(link_from_slack, data = payload)
                             
    print(response.text)
