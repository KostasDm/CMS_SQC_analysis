import pandas as pd
import numpy as np
from pretty_html_table import build_table
import SQC_analysis_tools as sqc
import argparse
from statistics import median
import yaml
import glob
import os
import SQC_data_analysis
import dash
import dash_table
from dash.dependencies import Input, Output
import dash_core_components as dcc
import dash_html_components as html
import plotly.express as px



parameters = {    'istrip': ['Strip Current', 'Istrip', '[pA]'],
                  'rpoly': ['Polysilicon Resistance', 'Rpoly', '[M$\Omega$]'],
                  'idark': ['Dark Current', 'Idark', '[nA]'],
                  'cac': ['Coupling Capacitance', 'Cac', '[pF]'],
                  'cint': ['Interstrip Capacitance', 'Cint', '[pF]'],
                  'rint': ['Interstrip Resistance', 'Rint', '[G$\Omega$]'],
                  'idiel': ['Dielectric Current', 'Idiel', '[pA]']}

qualification_parameters = {'Istrip': 'Leaky strips',
                            'Rpoly': 'High Rpoly',
                            'Cac': 'Low Cac',
                            'Idiel': 'Pinholes',
                            'Rint': 'Low Rint',
                            'Cint': 'Cint'}




def read_config():
    with open('SQC_parameters.yml', 'r') as f:
        conf = yaml.load(f, Loader=yaml.FullLoader)

    return conf




def IV_analysis(filename):

    dict2 = sqc.get_parameter(filename, 'current', True)
    dict2['Voltage'] = np.abs(dict2['Voltage'])
    idx_600 = np.where((dict2['Voltage'] >599) & (dict2['Voltage'] <601)) #v.index[v.between(599,601)]
    idx_800 = np.where((dict2['Voltage'] >799) & (dict2['Voltage'] <801)) #v.index[v.between(799,801)]


    i600=dict2['current'][int(idx_600[0])]
    i800=dict2['current'][int(idx_800[0])]

    i_ratio = i800/i600

    return i600, i800, i_ratio


def Vfd_analysis(filename):

    dict3 = sqc.get_parameter(filename, 'capacitance', True)
    dict3['Voltage'] = np.abs(dict3['Voltage'])

    dict3['capacitance'] = np.abs(dict3['capacitance'])
    dict3['capacitance'] = [1/(i**(2)) for i in dict3['capacitance']]

    v_dep1, v_dep2, rho = sqc.analyse_cv(dict3['Voltage'] , dict3['capacitance'] )

    return v_dep2



def Istrip_analysis(filename, istrip, conf):

    leaky_number = 0
    #istrip = (istrip*1e12).abs()

    i_median = np.median(istrip)
    i_mad = sqc.MAD(istrip, i_median)


    for i in istrip:
      if 'PSS' in filename:
        if np.abs(i)>= conf['Strip_Parameters']['Istrip']['PSS_threshold']:
            leaky_number +=1

      elif '2-S' in filename:
          
          if np.abs(i)>=conf['Strip_Parameters']['Istrip']['2S_threshold']:
              leaky_number +=1


    return i_median, i_mad, leaky_number



def Rpoly_analysis(filename, rpoly, conf):


    r_median = np.median(rpoly)
    r_mad = sqc.MAD(rpoly, r_median)

    outliers_rpoly=0

    for r in rpoly:

        if ~np.isclose(r, conf['Strip_Parameters']['Rpoly']['2S_threshold'], atol=0.5):
            outliers_rpoly +=1

    return r_median, r_mad, outliers_rpoly



def Idark_analysis(filename, idark, conf):


    i_median = np.median(idark)
    sigma_i = np.std(idark)

    return i_median, sigma_i, 0



def Cac_analysis(filename, cac, conf):

    outliers_cac =0

    c_median = np.median(cac)
    
    cac_mad = sqc.MAD(cac, c_median)

    for c in cac:
      if 'PSS' in filename:
        if c<conf['Strip_Parameters']['Cac']['PSS_threshold']:
            outliers_cac +=1

      elif '2S' in filename:
        if c<conf['Strip_Parameters']['Cac']['2S_threshold']:
            outliers_cac += 1

    return c_median, cac_mad, outliers_cac



def Idiel_analysis(filename, idiel, conf):

    pinholes =0


    i_median = np.median(idiel)
    i_mad = sqc.MAD(idiel, i_median)

    for i in idiel:
        if i>=conf['Strip_Parameters']['Idiel']['2S_threshold']:

            pinholes +=1

    return i_median, i_mad, pinholes


def Cint_analysis(filename, cint, conf):

    outliers_cint = 0
    c_median = np.median(cint)
    cint_mad = sqc.MAD(cint, c_median)

    for c in cint:
        if c>conf['Strip_Parameters']['Cint']['2S_threshold']:
            outliers_cint +=1

    return c_median, cint_mad, outliers_cint



def Rint_analysis(filename, rint, conf):
    outliers_rint = 0

    r_median = np.median(rint)
    rint_mad = sqc.MAD(rint, r_median)

    for r in rint:
        if r < conf['Strip_Parameters']['Rint']['2S_threshold']:
            outliers_rint += 1

    return r_median, rint_mad, outliers_rint



def compile_table_stripscan(dict, qual_dict, xlabel, conf, filename):



    labels=[]

    list_with_median_strings = []
    list_with_outliers = []
    median_list = []

    def make_list_with_median(file, parameter, data, conf, li, median_list, list_with_outliers):

        method = getattr(SQC_data_analysis, parameter + '_analysis')(file, data, conf)
        med, mad, outliers = method[0], method[1], method[2]
        median_list.append(float(med))
        list_with_median_strings.append('{:.2f} \u00B1 {:.2f}'.format(med, mad))  # \u00B1
        list_with_outliers.append(outliers) #$\pm$

        return median_list, list_with_median_strings, list_with_outliers



    for file in filename:

      if 'Str' in file:

        base = os.path.basename(file)
        lbl1 = os.path.splitext(base)[0]
        lbl, batch = sqc.assign_label(file)

        #lbl2 = lbl.replace("_", "\\textunderscore")
        labels.append(lbl)


        dict2 = sqc.get_parameter(file, xlabel, True)

        median_list, list_with_median_strings, list_with_outliers = make_list_with_median(file, xlabel, dict2[xlabel], conf, list_with_median_strings, median_list, list_with_outliers)

    labels.append('Batch Median')

    med = np.array(median(median_list))
    list_with_median_strings.append('{:.2f} \u00B1 {:.2f}'.format(median(median_list), sqc.numpy_MAD(median_list, med) ))

    if xlabel !='Idark':
        dict.update({'Sensor': labels})
        dict.update({xlabel + ' ' + '[' + conf['Strip_Parameters'][xlabel]['units'] +']': [i for i in list_with_median_strings]})
        for key, values in qualification_parameters.items():
            if xlabel==key:
                  qual_dict.update({'Sensor': labels[:-1]})
                  qual_dict.update({values: [i for i in list_with_outliers]})


    return dict, labels, qual_dict, batch


def compile_table_IVCV(filename):



    dict =({})
    li = []
    labels=[]
    iter =-1
    it = 0
    for file in filename:
      if 'IVC' in file:

        base = os.path.basename(file)
        lbl1 = os.path.splitext(base)[0]
        lbl, batch = sqc.assign_label(file)
        labels.append(lbl)
        iter +=1

        i600, i800, i_ratio = IV_analysis(file)
        v_fd = Vfd_analysis(file)

        li.append([float(i600), float(i800), float(i_ratio), v_fd])
    labels.append('Median')
    df = pd.DataFrame({'Sensor': labels})
    li.append([np.median([li[i][0] for i in range(iter+1)]), np.median([li[i][1] for i in range(iter+1)]), np.median([li[i][2] for i in range(iter+1)]), np.median([li[i][3] for i in range(iter+1)])])

    dict.update({'i600 [nA]' : [round(li[i][0],2) for i in range(iter+2)],
                'i800 [nA]' :  [round(li[i][1],2) for i in range(iter+2)],
                'i800/i600' : [round(li[i][2],2) for i in range(iter+2)],
                'V_fd [V]': [round(li[i][3],2) for i in range(iter + 2)]
    })

    for key, values in dict.items():
        it += 1
        df.insert(it, '{}'.format(key), values, True)



    return df


def make_latex_table(df1, df2, df3):


    with open("my_table.tex", "w") as f:

        f.write("\\scalebox{0.6}{\\begin{tabular}{" + " | ".join(["c"] * len(df1.columns)) + "}\n")

        f.write(" & ".join([str(x) for x in df1.columns]) + " \\\\\n")
        f.write("\\hline")
        for i, row in df1.iterrows():
            f.write(" & ".join([str(x) for x in row.values]) + " \\\\\n")
        f.write("\\end{tabular}}")
        f.write("\\\\")
        f.write("\\vspace{0.3in}")

        f.write("\\scalebox{0.6}{\\begin{tabular}{" + " | ".join(["c"] * len(df2.columns)) + "}\n")

        f.write(" & ".join([str(x) for x in df2.columns]) + " \\\\\n")
        f.write("\\hline")
        for i, row in df2.iterrows():
            f.write(" & ".join([str(x) for x in row.values]) + " \\\\\n")
        f.write("\\end{tabular}}")



def generate_tables(conf, app, filename):

   dict = {}
   qual_dict = {}
   for values in conf['IVCV_Parameters']:
       if values == 'capacitance' or values =='current':
           ivc_dataframe = compile_table_IVCV(filename)
   for values in conf['Strip_Parameters']:
           dict, labels, dict_qual, batch = compile_table_stripscan(dict, qual_dict, values, conf, filename)


   new_dict = pd.DataFrame.from_dict(dict)
   dict_qual2 = pd.DataFrame.from_dict(dict_qual)
   
   html_table_blue_light = build_table(new_dict, 'blue_light', text_align='center')
   html_table_blue_light_2 = build_table(dict_qual2, 'blue_light', text_align='center')
   html_table_blue_light_3 = build_table(ivc_dataframe, 'blue_light', text_align='center')

   with open('sqc_tables_batch_{}.html'.format(batch), 'w', encoding="utf-8") as f:
       f.write("<html><body> <h1>SQC Parameters Batch <font color = #4000ff>{}</font></h1>\n</body></html>".format(batch))
       f.write("\n")
       f.write(html_table_blue_light + "\n" + html_table_blue_light_2 +"\n" + html_table_blue_light_3)




   app_layout1 = html.Div([
                        html.Div(children=[
                            html.H1(children='Strip Parameters batch {}'.format(batch)),
                            dash_table.DataTable(id='SQC_Parameters',
                                               columns=[{"name": i, "id": i}
                                               for i in new_dict.columns],
                                               data=new_dict.to_dict('records'),
                                               style_cell={'textAlign': 'center'},
                                               style_header={'backgroundColor': 'rgb(0, 191, 255)',
                                                             'fontWeight': 'bold'},
                                               export_format='xlsx',
                                               export_headers='display',
                                               merge_duplicate_headers=True
                                               #style_data=dict(backgroundColor="lavender")
                                               )
                                               ], style={'width': '70%', 'display': 'inline-block'}),
                        html.Div([dash_table.DataTable(id='SQC_Qual_Parameters',
                                                 columns=[{"name": i, "id": i}
                                                          for i in dict_qual2.columns],
                                                 data=dict_qual2.to_dict('records'),
                                                 style_cell={'textAlign': 'center'},
                                                 style_header={'backgroundColor': 'rgb(0, 191, 255)',
                                                               'fontWeight': 'bold'},
                                                 export_format='xlsx',
                                                 export_headers='display',
                                                 merge_duplicate_headers=True
                                                 # style_data=dict(backgroundColor="lavender")
                                                 )
                            ], style={'width': '70%', 'display': 'inline-block'}),
                        html.Div([dash_table.DataTable(id='SQC_IVC_Parameters',
                                      columns=[{"name": i, "id": i}
                                               for i in ivc_dataframe.columns],
                                      data=ivc_dataframe.to_dict('records'),
                                      style_cell={'textAlign': 'center'},
                                      style_header={'backgroundColor': 'rgb(0, 191, 255)',
                                                    'fontWeight': 'bold'},
                                      export_format='xlsx',
                                      export_headers='display',
                                      merge_duplicate_headers=True
                                      # style_data=dict(backgroundColor="lavender")
                                      ) ], style={'width': '70%', 'display': 'inline-block'}),
                        html.Div(id='page-1-content'),
                        html.Br(),
                        dcc.Link('Go to Strip parameters Plots', href='/page-2'),
                        html.Br(),
                        dcc.Link('Go to IVCV Plots', href='/page-3'),
                        html.Br(),
                        dcc.Link('Go back to home', href='/'),
                                   ])
   return app_layout1



def generate_strip_graphs(config, app2, filename):



    dict_with_dfs = {}
    labels=[]

    for file in filename:
      if 'Str' in file:
        prefix = '_'.join(os.path.splitext(os.path.basename(os.path.normpath(file)))[0].split('_')[0:1])
        headers = config['headers']['IV' if prefix == 'IVC' else 'Str']
        base = os.path.basename(file)
        lbl1 = os.path.splitext(base)[0]
        lbl, batch = sqc.assign_label(file)

        labels.append(lbl)

        df = sqc.convert_txt_to_df(file, headers, 23 if '2-S' in file else 16)
        df = df.abs()
        lazy_list = [lbl]*len(df)
        df['Sensor'] = lazy_list
        dict_with_dfs.update({lbl: df})

    mega_df = pd.concat(dict_with_dfs)

    app2_layout = html.Div([
          html.H1('SQC Parameter Analysis'),
          dcc.Dropdown(id='dropdown',
                     options=[{'label': i, 'value': i} for i in config['Strip_Parameters']],
                     value='Istrip'),
          dcc.Graph(id='my_graph', figure=px.scatter(mega_df, x=mega_df.loc[labels]['Pad'], y=mega_df.loc[labels]['Istrip'], template = "ggplot2")),

          html.Div(id='page-2-content'),
          html.Br(),
          dcc.Link('Go to Tables', href='/page-1'),
          html.Br(),
          dcc.Link('Go to IVCV Plots', href='/page-3'),
          html.Br(),
          dcc.Link('Go back to home', href='/')
        ])


    @app2.callback(
        Output(component_id='my_graph', component_property='figure'),
        Input(component_id='dropdown', component_property='value')
    )
    def update_graph(parameter):

        fig2 = px.scatter(df, x=mega_df.loc[labels]['Pad'], y=mega_df.loc[labels][parameter], color = mega_df.loc[labels]['Sensor'], template = "ggplot2" )
        fig2.update_yaxes(title_text='{0} [{1}] '.format(parameter, config['Strip_Parameters'][parameter]['units']), title_font_family="Times New Roman", title_font_size=20)
        fig2.update_xaxes(title_text='Pad', title_font_family="Times New Roman", title_font_size=20)
        fig2.update_xaxes(type='category')
        return fig2

    return app2_layout


def generate_ivc_graphs(config, app2, filename):


    dict_with_dfs = {}
    labels=[]

    for file in filename:
      if 'IVC' in file:
        prefix = '_'.join(os.path.splitext(os.path.basename(os.path.normpath(file)))[0].split('_')[0:1])
        headers = config['headers']['IV' if prefix == 'IVC' else 'Str']
        base = os.path.basename(file)
        lbl1 = os.path.splitext(base)[0]
        lbl, batch = sqc.assign_label(file)

        labels.append(lbl)

        df = sqc.convert_txt_to_df(file, headers, 9)

        df = df.abs()
        lazy_list = [lbl]*len(df)
        df['Sensor'] = lazy_list
        dict_with_dfs.update({lbl: df})

    iv_df = pd.concat(dict_with_dfs)


    app2_layout = html.Div([
          html.H1('SQC Parameter Analysis'),
          dcc.Dropdown(id='dropdown2',
                     options=[{'label': i, 'value': i} for i in config['IVCV_Parameters']],
                     value='current'),
          dcc.Graph(id='my_graph2', figure=px.scatter(iv_df, x=iv_df.loc[labels]['Voltage'].round(1), y=iv_df.loc[labels]['current'], template = "ggplot2")),

          html.Div(id='page-3-content'),
          html.Br(),
          dcc.Link('Go to Tables', href='/page-1'),
          html.Br(),
          dcc.Link('Go to Strip parameters plots', href='/page-2'),
          html.Br(),
          dcc.Link('Go back to home', href='/')
        ])


    @app2.callback(
        Output(component_id='my_graph2', component_property='figure'),
        Input(component_id='dropdown2', component_property='value')
    )
    def update_graph(parameter):

        if parameter == 'capacitance':
            iv_df[parameter] = 1/(iv_df[parameter].pow(2))
        color_seq = ['#636EFA', '#EF553B', '#00CC96', '#AB63FA', '#FFA15A', '#19D3F3', '#FF6692', '#B6E880', '#FF97FF', '#FECB52',
                    '#1F77B4', '#FF7F0E', '#2CA02C', '#D62728', '#9467BD', '#8C564B', '#E377C2', '#7F7F7F', '#BCBD22', '#17BECF']

        fig2 = px.scatter(iv_df, x=iv_df.loc[labels]['Voltage'].round(1), y=iv_df.loc[labels][parameter], color = iv_df.loc[labels]['Sensor'], color_discrete_sequence = color_seq,template = "ggplot2" )
        fig2.update_yaxes(title_text='{0} [{1}] '.format(parameter, config['IVCV_Parameters'][parameter]['units']), title_font_family="Times New Roman", title_font_size=20)
        fig2.update_xaxes(title_text='Voltage', title_font_family="Times New Roman", title_font_size=20)
        fig2.update_xaxes(type='category')
        return fig2

    return app2_layout


def parse_args():

    parser = argparse.ArgumentParser()
    parser.add_argument('path')
    return parser.parse_args()



def main():



   conf = read_config()
   args = parse_args()


   #for subdirs, dirs, files in os.walk(args.path):
   path = args.path
   filename = glob.glob(path + os.sep + '*.txt')
  
   
   app = dash.Dash(__name__, suppress_callback_exceptions=True)
   page_1_layout = generate_tables(conf, app, filename)
   '''
   app.layout = html.Div([
       dcc.Location(id='url', refresh=False),
       html.Div(id='page-content')
   ])

   index_page = html.Div([
       dcc.Link('Go to Tables', href='/page-1'),
       html.Br(),
       dcc.Link('Go to Strip parameters Plots', href='/page-2'),
       html.Br(),
       dcc.Link('Go to IVCV Plots', href='/page-3')
   ])
   page_1_layout = generate_tables(conf, app, filename)
   page_2_layout = generate_strip_graphs(conf, app, filename)
   page_3_layout = generate_ivc_graphs(conf, app, filename)

   @app.callback(dash.dependencies.Output('page-content', 'children'),
                 [dash.dependencies.Input('url', 'pathname')])
   def display_page(pathname):
       if pathname == '/page-1':
           return page_1_layout
       elif pathname == '/page-2':
           return page_2_layout
       elif pathname == '/page-3':
           return page_3_layout
       else:
           return index_page

   app.run_server(debug=True)
   '''


if __name__ == "__main__":

    main()



