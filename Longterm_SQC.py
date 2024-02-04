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


hv.extension('bokeh')



def make_dataframe_from_ascii(datafile, skip):

    data = np.genfromtxt(datafile, skip_header=skip, delimiter=",", encoding='latin-1') 

    df = pd.DataFrame(data, columns= ['Timestamp', 'Voltage', 'Current', 'smu_current [A]', 'pt100', 'cts_temp', 'cts_humi', 'cts_status', 'cts_program', 'hv_status']) #'smu_current [A]'

    return df



def plot_Ivstime(df, label, color, style):
    # plot the time evolution of current

    df['Current'] = (df['Current'].abs())*1e9

 
    df1 = pd.DataFrame({'Time [h]': df['Timestamp'].divide(3600), 'Current [nA]': df['Current'].values})
    plot = (hv.Curve(df1, label=label)).opts(width=800, height = 600, line_width=5, title = 'Current over time', fontsize={'title': 15, 'labels': 14, 'xticks': 12, 'yticks': 12})#, ylim=(0, 150)
    
   
    return plot



def plot_IV(df, label, color):
    # plot the IV

    df1 = pd.DataFrame({'Voltage [V]': df['Voltage'].abs(), 'Current [nA]': ((df['Current'].abs())*1e9).values})
 
    
    plot = (hv.Curve(df1, label=label)).opts(width=800, height=600, line_width=3, title='IV curve',
                                             fontsize={'title': 15, 'labels': 14, 'xticks': 12, 'yticks': 12})

    return plot




def plot_temp_humi(df):

    df['Timestamp'] = df['Timestamp'].divide(3600)
    df_temp = pd.DataFrame({'Time [h]': df.get('Timestamp'), 'Temperature [\u00B0C]': df.get('pt100').values})
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
    c_sec = hv.Curve(df_humi, name = 'Rel. Humidity [%]', label = 'Humidity' ).options(color='blue', width=800, height = 600,  fontsize={'title': 15, 'labels': 14, 'xticks': 12, 'yticks': 12}) #, hooks=[apply_formatter])
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
    fig, ax = plt.subplots()
    c = ['golden', 'red', 'blue', 'black']
    for f in files:

        file = f.split(os.sep)[-1]
        sensor = '_'.join(os.path.splitext(file)[0].split('_')[0:4])
        sensor = '-'.join(os.path.splitext(sensor)[0].split('-')[1:3]) if '2-S' in sensor else '-'.join(
            os.path.splitext(sensor)[0].split('-')[1:2])

        if "it" in f:
            print(f)
            index_it += 1

            df = make_dataframe_from_ascii(f, 200) #185
            
            relative_deviation, status = find_relative_deviation(df)
            LT_list.append([sensor, round(relative_deviation,2), status])
            
            print('The relative deviation of sensor {} is: {} %'.format(sensor, round(relative_deviation,2)))
            
            plot_it_list.append(plot_Ivstime(df, sensor, colors[index_it], '-'))
            
           
            df = df.loc[df['cts_temp']<20.5]
            
            plt.plot(df['Timestamp'].div(3600), df['Current'].abs(), '-o', color=colors[index_it], label = sensor)
            plt.xlabel('Time [h]', fontsize=13)#, fontweight = 'bold')
            plt.ylabel('Current [nA]', fontsize=13)#, fontweight = 'bold')
            


        if "IV" in f:
          
            index_iv += 1

            df1 = make_dataframe_from_ascii(f, 9)
            plot_iv_list.append(plot_IV(df1, sensor, colors[index_iv]))
    
    
    plt.legend(loc='best')
    plt.show()
    dataframe = pd.DataFrame(data = LT_list, columns=['Sensor', 'Leakage Current relative deviation [%]', 'Status'])
    make_table_with_LT_results(dataframe)
    
    
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
       new_plot2 = hv.Layout( IV_plot + new_plot + humi ).cols(1) 
       new_plot2.opts(shared_axes=False)
       renderer = hv.renderer('bokeh')
       renderer.save(new_plot2, 'LT_figures')

       final_plot = renderer.get_plot(new_plot2).state
      
       #show(final_plot)#, gridplot(children = humi, ncols = 1, merge_tools = False))


       plot_iv_list.clear()
      



if __name__ == "__main__":
    main()