#!/usr/bin/env python3
'''
sentimentanalyser.py
euforia_eu_forecast_sentiment_analysis 
6/6/18
Copyright (c) Gilles Jacobs. All rights reserved.  
'''
from sentiment_analysis import datahandler, settings, preprocessor, lexicoder
import pandas as pd
import pysentiment as ps
import matplotlib as plt
import os
from sklearn.preprocessing import MinMaxScaler, scale, maxabs_scale
from matplotlib.pyplot import *

def compute_subjectivity_score(s_pos, s_neg, n_tok, epsilon = 1e-6):
    sub = (s_pos + s_neg) * 1.0 / (n_tok + epsilon)
    return sub

def compute_polarity_score(s_pos, s_neg, epsilon = 1e-6):
    pol = (s_pos - s_neg) * 1.0 / ((s_pos + s_neg) + epsilon)
    return pol

def scale(series, scale_func=maxabs_scale):
    return scale_func(series)

def plot_state_polarity(df):
    # plot polarity value over time
    df.set_index('date', inplace=True)
    df.groupby('state')['mcdlou_polarity_subjweight'].plot(legend=True)
    plt.pyplot.show()
    df.reset_index()
    # make mean error plot
    mean =  df.groupby('state')['mcdlou_polarity_subjweight'].mean()
    std = df.groupby('state')['mcdlou_polarity_subjweight'].std()
    mean.name, std.name = f"mean_{mean.name}", f"std_{std.name}"
    df_error = pd.concat([mean, std], axis=1)
    df_error[mean.name].plot(fmt='ro', yerr=df_error[std.name], grid='on')
    states = list(df.groupby('state').groups.keys())
    tick_marks = np.arange(len(states))
    plt.pyplot.xticks(tick_marks, states, rotation=90)
    plt.pyplot.show()


def weight_subjectivity(df):

    columns_to_weight = [c for c in df.columns if "polarity" in c]
    weight_columns = [c for c in df.columns if "subjectivity" in c]
    for c_pol, c_subj in zip(columns_to_weight, weight_columns):
        df[f"{c_pol}_subjectivity_weighted"] = df[c_pol] * scale(df[c_subj])
        # df[f"{c_pol}_subjectivity_weighted_scaled"] = scale(df[f"{c_pol}_subjectivity_weighted"])
    return df

def sa_hiv4(txt):
    hiv4 = ps.HIV4()
    tokens = hiv4.tokenize(txt)  # text can be tokenized by other ways
    # however, dict in HIV4 is preprocessed
    # by the default tokenizer in the library
    score = hiv4.get_score(tokens)
    print(f"{txt[:50]}...{txt[-50:]}\n{score}")
    return score

def sa_mcdlou(txt):
    lm = ps.LM()
    tokens = lm.tokenize(txt)
    score = lm.get_score(tokens)
    print(f"{txt[:50]}...{txt[-50:]}\n{score}")
    return score

def combine_title_text(row):
    if isinstance(row["title"], str):
        return row["title"] + ". " + row["text"]
    else:
        return row["text"]

if __name__ == "__main__":
    # do analysis from scratch if setting is set or if processed opt data absent
    if settings.FROM_SCRATCH or not os.path.exists(settings.OPT_FP):
        df = datahandler.read_data(settings.DATASET_FP)
        df = datahandler.clean_dataset(df)
        # combine title and text
        df["alltext"] = df.apply(lambda row: combine_title_text(row), axis=1)
        # add lexicoder sa output
        df = lexicoder.add_lexicoder(df)
        # add python sa mcdlou and hiv4
        df["mcdlou_score"] = df["alltext"].apply(sa_mcdlou)
        df["hiv4_score"] = df["alltext"].apply(sa_hiv4)
        # make returned mcdlou scores easier to work with in df
        df = pd.concat([df.drop(["mcdlou_score"], axis=1), df["mcdlou_score"].apply(pd.Series).add_prefix("mcdlou_")], axis=1)
        df = pd.concat([df.drop(["hiv4_score"], axis=1), df["hiv4_score"].apply(pd.Series).add_prefix("hiv4_")],
                       axis=1)
        df.columns = map(str.lower, df.columns)
        # average all polarity columns
        df["avg_polarity"] = df[[col for col in df.columns if 'polarity' in col]].mean(axis=1)
        # write data
        datahandler.write_data(df, settings.OPT_FP)
    else:
        df = datahandler.read_data(settings.OPT_FP)

    # Combine and plot
    # weight polarity by subjectivity and rescale
    df["mcdlou_polarity_subjweight"] = df['mcdlou_polarity']*df["mcdlou_subjectivity"]
    df['mcdlou_polarity_subjscale'] = scale(df['mcdlou_polarity']*df["mcdlou_subjectivity"], scale_func=maxabs_scale)
    df['hiv4_polarity_subjscale'] = scale(df['hiv4_polarity']*df["hiv4_subjectivity"], scale_func=maxabs_scale)
    print(df.ix[df['mcdlou_polarity'].idxmax()], df.ix[df['mcdlou_polarity'].idxmin()])
    print(df.ix[df['mcdlou_polarity_subjscale'].idxmax()], df.ix[df['mcdlou_polarity_subjscale'].idxmin()])

    plot_state_polarity(df)