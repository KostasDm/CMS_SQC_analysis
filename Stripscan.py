import SQC_analysis_tools as sqc
import matplotlib.pyplot as plt
import glob
import os
import argparse
from matplotlib.backends.backend_pdf import PdfPages


## parameters: { function name : [title, parameter, SI unit] }

parameters = {'istrip': ['Strip Current', 'Istrip', 'A'],
              'rpoly': ['Polysilicon Resistance', 'Rpoly', '\u03A9'],
              'idark': ['Total Current', 'Idark', 'A'],
              'cac': ['Coupling Capacitance', 'Cac', 'F'],
              'cint': ['Interstrip Capacitance', 'Cint', 'F'],
              'idiel': ['Dielectric Current', 'Idiel', 'A'],
              'rint': ['Interstrip Resistance', 'Rint', '\u03A9'],
              'temp': ['Temperature during measurement', 'Temperature', '\u00B0C'],
              'humi': ['Humidity during measurement', 'Humidity', '%']}

color = ['red', 'blue', 'black', 'gold', 'purple', 'green', 'violet', 'peru', 'lightskyblue',
         'pink', 'slategray', 'lime', 'lightgreen', 'cyan', 'brown', 'darkcyan',  'lightgray']



def get_parameter(filename, parameter):

   

     if '2-S' in filename:
        sensor_id = '2-S'
     else:
        sensor_id = 'PSS'

     df = sqc.make_Dataframe_Stripscan(parameter, filename, sensor_id)

    
     strip = df['Pad']
     parameter = df[parameter]

     return strip, parameter



def overlay_graphs(filename, title, xlabel, ylabel, unit):

 
    ind =-1
    figs = []
    
  
    for file in filename:
      
      if 'Str' in file:
         
         base = os.path.basename(file)
         lbl=os.path.splitext(base)[0]
         
         x, y = get_parameter(file, ylabel)
         y_norm, y_unit = sqc.normalise_parameter(y, str(unit))
         
        
         ind +=1

         sqc.plot_graph(x, abs(y_norm), '{}'.format(color[ind]), lbl, title, xlabel, ylabel + ' ' +'[{}]'.format(y_unit))
         
         if (y_norm.abs()).max() > (10*y_norm.abs()).median():
         
          plt.yscale('log')

   





def parse_args():

    parser = argparse.ArgumentParser('a path to directory containing ascii files to be analysed')
    parser.add_argument('path')
    return parser.parse_args()


def main():

    args = parse_args()
   
    filename = glob.glob(args.path + os.sep + '*.txt')
    list_of_figures = []
    stripscan_config = sqc.read_config()['Strip_Parameters']

    with PdfPages('stripscan.pdf') as pdf:
      for key,values in stripscan_config.items():
         
         fig = plt.figure()
         overlay_graphs(filename, values['title'], 'Pad #', key, values['units'])
         pdf.savefig(fig)

          
          
if __name__ == "__main__":
    main()
