import pandas as pd
import os
import sys
import argparse
import numpy as np
import glob
import matplotlib.pyplot as plt
import holoviews as hv
from bokeh.io import  output_file, show
from bokeh.models import LinearAxis, Range1d
from bokeh.models.renderers import GlyphRenderer
from pretty_html_table import build_table
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

hv.extension('bokeh')



def make_dataframe_from_ascii(datafile, skip):

    data = np.genfromtxt(datafile, skip_header=skip, delimiter=",", encoding='latin-1') #max_rows=621

    df = pd.DataFrame(data, columns= ['Timestamp', 'Voltage', 'Current', 'smu_current [A]', 'pt100', 'cts_temp', 'cts_humi', 'cts_status', 'cts_program', 'hv_status']) #

    return df


def scale_current(df):
   
   df['cts_temp'] = pd.to_numeric(df['cts_temp'])
   df_troom= df.loc[df['cts_temp']>19.0]
   df_cold= df.loc[df['cts_temp']<-28.0]
   i20 = df_troom['Current'].median()
   icold = df_cold['Current'].median()
   print(icold)
   kb = 8.617*1e-5
   Eeff = 1.21
   i_30 = i20/(((293**2)*np.exp((-Eeff/(2*kb*293))))/((243**2)*np.exp((-Eeff/(2*kb*243)))))
   
   i_cold_std = df_cold['Current'].std()
   return icold, i_cold_std, i_30
 
   

def plot_Ivstime(df, label, color, style):
    # plot the time evolution of current

    
    df['Current'] = (df['Current'].abs())*1e9
 
    df1 = pd.DataFrame({'Time [h]': df['Timestamp'].divide(3600), 'Current [nA]': df['Current'].values})
    plot = (hv.Curve(df1, label=label)).opts(logy=True,width=900, height = 600, line_width=5, title = 'Current over time', fontsize={'title': 15, 'labels': 17, 'xticks': 15, 'yticks': 15})
    
   
    return plot



def plot_IV(df, label, color):
    # plot the IV

    df1 = pd.DataFrame({'Voltage [V]': df['Voltage'].abs(), 'Current [nA]': ((df['Current'].abs())*1e9).values})
 
    
    plot = (hv.Curve(df1, label=label)).opts(width=800, height=600, line_width=3, title='IV curve',
                                             fontsize={'title': 15, 'labels': 14, 'xticks': 12, 'yticks': 12})

    return plot




def plot_temp_humi(df):

    df['Timestamp'] = df['Timestamp'].divide(3600)
    df_temp = pd.DataFrame({'Time [h]': df.get('Timestamp'), 'Temperature [\u00B0C]': df.get('cts_temp').values})
    df_humi = pd.DataFrame({'Time [h]': df.get('Timestamp'), 'Rel. Humidity [%]': df.get('cts_humi').values})



    def apply_formatter(plot):
        # this function is necessary for the construction of the second y-axis --> humidity axis
        p = plot.state

        # create secondary range and axis
        p.extra_y_ranges = {"twiny": Range1d(start=0, end=60)}
        p.add_layout(LinearAxis(y_range_name="twiny", axis_label="Rel. Humidity [%] ", axis_label_text_color='blue'), 'right')

        # set glyph y_range_name to the one we've just created
        glyph = p.select(dict(type=GlyphRenderer))[0]
        glyph.y_range_name = "twiny"


    c_def = hv.Curve(df_temp , name='Temperature [\u00B0C]', label = 'Temperature').options(color='red', width=800, height = 600, title = 'Environmental conditions over time', fontsize={'title': 15, 'labels': 14, 'xticks': 12, 'yticks': 12})
    c_sec = hv.Curve(df_humi, name = 'Rel. Humidity [%]' ).options(color='blue', width=900, height = 600,  fontsize={'labels': 17, 'xticks': 15, 'yticks': 15}) #, hooks=[apply_formatter])
    plot = c_def + c_sec #+ c_def*c_sec

    return plot


def find_relative_deviation(df):


    relative_deviation = np.abs(100*(df['Current'].max() - df['Current'].min())/(df['Current'].mean()))
   
    if relative_deviation<30.0:
        status='OK'
    else:
        status = 'Noisy'
        
    return relative_deviation, status
    

def make_table_with_LT_results(df):


   html_table_blue_light = build_table(df, 'blue_light', text_align='center')
   with open('LT_status_table.html', 'w') as f:
       f.write("<html><body> <h1>LongTerm test Status <font color = #4000FF>{}</font></h1>\n</body></html>")
       f.write("\n")
       f.write(html_table_blue_light)
       



def return_current(df):
    df['Current'] = df['Current'] * 1e9

    return df['Current'], df



def parse_args():

    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    return parser.parse_args()


def make_color_list():

    colors = []
    evenly_spaced_interval = np.linspace(0, 1, 10)
    for x in evenly_spaced_interval:
        colors.append(plt.cm.tab10(x))

    return colors


def create_list_with_plots(files):

    index_it = 0
    index_iv = 0

    colors = make_color_list()
   
    plot_iv_list = []
    plot_it_list = []

    df = pd.DataFrame({})
    df1 = pd.DataFrame({})
    LT_list=[]
    ind=[]
    sensors=[]
    fig, ax = plt.subplots()
    for f in files:

        file = f.split(os.sep)[-1]
        sensor = '_'.join(os.path.splitext(file)[0].split('_')[0:4])
        sensor = '-'.join(os.path.splitext(sensor)[0].split('-')[1:3]) if '2-S' in sensor else '-'.join(
            os.path.splitext(sensor)[0].split('-')[1:2])

        if "it" in f:
            sensor_plot = '_'.join(sensor.split('_')[0:2])
            index_it += 1

            df = make_dataframe_from_ascii(f, 9) #185
            
            relative_deviation, status = find_relative_deviation(df)
            LT_list.append([sensor, round(relative_deviation,2), status])
            
            print('The relative deviation of sensor {} is: {} %'.format(sensor, round(relative_deviation,2)))
            
            plot_it_list.append(plot_Ivstime(df, sensor, colors[index_it], '-'))
            icold, icold_std, i30 = scale_current(df)
            legend_elements = [Line2D([0], [0],  marker='*', color='b', label='Theoretical', markersize=8, linestyle='None'),
                   Line2D([0], [0], marker='o', color='b', label='Experimental', markersize=8)]
              
            p = index_it-1               
            ind.append(p) 
            sensors.append(sensor_plot)            
            plt.errorbar(p, icold, yerr=icold_std, fmt='o', markersize=8, color=colors[index_it])
            plt.errorbar(x=p, y=i30, marker='*', markersize=8, color = colors[index_it])
           
            plt.ylabel('Bias current@-30\u2103 [nA]', fontsize= 12, fontweight='bold')
            #plt.xticks(rotation = 30, fontsize=7)
            ax.legend(handles=legend_elements)
            plt.grid()

        elif "IV" in f:
          
            index_iv += 1

            df1 = make_dataframe_from_ascii(f, 9)
            plot_iv_list.append(plot_IV(df1, sensor, colors[index_iv]))
    
    
    
    dataframe = pd.DataFrame(data = LT_list, columns=['Sensor', 'Leakage Current relative deviation [%]', 'Status'])
    make_table_with_LT_results(dataframe)
    
    plt.xticks(ind, sensors, rotation = 30, fontsize=7)
    plt.savefig('cold_run.pdf')
    plt.show()
    return plot_it_list, plot_iv_list, df, df1



def main():

    args = parse_args()
    
    fig_index=0
    for subdir, dirs, files in os.walk(args.path):

       if len(dirs)>=1:

           for dir in dirs:
               fig_index +=1
               files = glob.glob(args.path + os.sep + dir + os.sep + '*.txt')

               plot_it_list, plot_iv_list, df, df1 = create_list_with_plots(files)
               create_bookeh_plots(plot_it_list, plot_iv_list, df, fig_index)


       else:
            path = args.path

            files = glob.glob(path + os.sep + '*.txt')
            plot_it_list, plot_iv_list, df, df1 = create_list_with_plots(files)

            create_bookeh_plots(plot_it_list, plot_iv_list, df, fig_index)



def create_bookeh_plots(plot_it_list, plot_iv_list, df, fig_index):

       new_plot = hv.Overlay(plot_it_list)
       new_plot.opts(legend_position='right')
       new_plot.opts(norm={'axiswise': False})
       IV_plot = hv.Overlay(plot_iv_list)
       IV_plot.opts(legend_position='right')
       IV_plot.opts(norm={'axiswise': False})

      
       humi = plot_temp_humi(df)
       new_plot2 = hv.Layout( IV_plot+ humi + new_plot).cols(1)
       new_plot2.opts(shared_axes=False)
       renderer = hv.renderer('bokeh')
       renderer.save(new_plot2, 'LT_figures')

       final_plot = renderer.get_plot(new_plot2).state
      
       #show(final_plot)#, gridplot(children = humi, ncols = 1, merge_tools = False))


       plot_iv_list.clear()
      



if __name__ == "__main__":
    main()