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



headers_Stripscan = ['Pad', 'Istrip', 'Rpoly', 'Cac', 'Cac_Rp', 'Idiel', 'Cint', 'Cint_Rp', 'Idark', 'Rint', 'Temperature','Humidity']

headers_IVC = ['Voltage [V]',  'current [A]' , 'capacitance [F]', 'temperature [deg]', 'humidity [%]'] 

headers_HPK = ['Voltage [V]',  'current [A]']

headers_HPK_cv = ['Voltage [V]',  'capacitance [F]']




def read_config():
    with open('SQC_parameters.yml', 'r') as f:
        conf = yaml.load(f, Loader=yaml.FullLoader)

    return conf



def get_parameter(filename, parameter, clear):

    if '2-S' in filename:
        sensor_id = '2-S'
    else:
        sensor_id = 'PSS'

    dict = make_dictionary(parameter, filename, sensor_id)

    return dict



def make_dictionary(main_parameter, file, prefix):

    ### main_parameter: the parameter for which we will generate the xml file
    ### config: the configuration data
    ### file: the txt file to be analysed
    ### headers: the headers of the txt file data
    ### prefix: IVC or Str

    dict_with_values = {}
    config = read_config()
    prefix = '_'.join(os.path.splitext(os.path.basename(os.path.normpath(file)))[0].split('_')[0:1])


    headers = config['headers']['IV' if prefix == 'IVC' else 'Str']


    if 'Str' in file:

         a= convert_txt_to_df(file, headers, 23 if '2-S' in file else 16)

         df = a[a[main_parameter].notnull()]

         for secondary_parameter in config['Strip_Parameters'][main_parameter]['variables']:
            values = df[secondary_parameter].values

            if secondary_parameter in config['Strip_Parameters']:

              unit = float(config['Strip_Parameters'][secondary_parameter]['units_conversion'])
              values = [i*unit for i in values] #convert the list with data in the required from DB units

            dict_with_values[secondary_parameter] = values



    elif 'IVC' in file:
         a = convert_txt_to_df(file, headers, 9)
         for secondary_parameter in config['IVCV_Parameters'][main_parameter]['variables']:

           if main_parameter =='capacitance':
             df = a[a[main_parameter].notnull()]
             values = df[secondary_parameter].values
           else:
             values = a[secondary_parameter].values

           if secondary_parameter in config['IVCV_Parameters']:

             unit = float(config['IVCV_Parameters'][secondary_parameter]['units_conversion'])
             values = [i * unit for i in values]  #convert the list with data in the required from DB units

           dict_with_values[secondary_parameter] = values

    return dict_with_values



def convert_txt_to_df(filename, headers, skip):

    if 'HPK_' in filename:
        dat = np.genfromtxt(filename, skip_header=skip, max_rows=51)

    else:

        dat = np.genfromtxt(filename, skip_header= skip)

    df = pd.DataFrame(dat, columns = headers)

    return df


def make_Dataframe_Stripscan(parameter, filename, sensor_id):


    
    df= convert_txt_to_df(filename, headers_Stripscan, 23 if sensor_id=='2-S' else 16) #16
    df[parameter] = pd.to_numeric(df[parameter])
    df = df.dropna(subset=[parameter])

    return df



def make_Dataframe_IVCV(filename, start_line):

    if 'HPK_' in filename:
         df = convert_txt_to_df(filename, headers_HPK, start_line) 
    else:
         df = convert_txt_to_df(filename, headers_IVC, start_line) 
    #df = df.dropna()
    

    return df
   



def MAD(parameter, parameter_median):

    parameter_mad = np.median(np.abs(((parameter - parameter_median))))
    return parameter_mad



def assign_label(file):

    file = os.path.splitext(file)[0]

    lbl = '_'.join(file.split('_')[2:6])
    batch = '_'.join(lbl.split('_')[0:1])
  
  
    return lbl, batch



def plot_graph(x, y, color, label, title, xlab, ylab):

     
     plt.plot(x, y, '-o', color=color, markersize=4, label =label)
     plt.title(title, fontname="Times New Roman", fontsize=16, fontweight='bold')
     plt.xlabel(xlab, fontsize=12)
     plt.ylabel(ylab, fontsize=12)
   
     plt.tick_params(axis = 'y', labelsize=10)
     plt.tick_params(axis='x', labelsize=10)
    
     plt.legend(loc='best', fontsize=8, ncol=1)




def plot_scatter(x, y, color, label, title, xlab, ylab):

     plt.scatter(x,y, s=10, color= color, marker='o', label=label)
     plt.title(title)
     plt.xlabel(xlab)
     plt.ylabel(ylab)
     plt.ylim(0,1000)
     #plt.yscale('log')
     #plt.legend()




def plot_histogram(x, title, xlab, color, lbl):

    x_mean = np.median(x)
    x_std = stdev(x)
    x = np.clip(x, -2*x_mean, 2*x_mean)

    y1,x1, _ = plt.hist(x, bins=60, color=color, label=lbl)
    plt.xlabel(xlab, fontsize=15)
    plt.ylabel('Frequency', fontsize=15)
    plt.title(title, fontname="Times New Roman", fontsize=25, fontweight='bold')
    plt.legend()





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
    
    return v_dep1, v_dep2, rho



def units(data, unit):

    # This function converts the unit scale to the correct one

    x = np.median(abs(data))
    numer = 0
    unit_scale = ['P', 'T', 'G', 'M', 'k', '', 'm', '$\mu$', 'n', 'p', 'f', 'a', 'z', 'y']
    i = -1
    lower_limit = 1e-24

    max_scale = 1e+18
    while max_scale> lower_limit:
          previous_max = max_scale
          max_scale = max_scale/1000
          i +=1
          if x >= max_scale and x< previous_max:
             numerator = max_scale
             string = '{}{}'.format(unit_scale[i], unit)

    return numerator, string


def normalise_parameter(parameter, unit):

    # This function scales the data and return the latter and the units in the correct form

    denominator, unit = units(parameter, unit)
    #x = np.array([j / denominator for j in parameter])
    x = parameter.divide(denominator)
    
    return x, unit



