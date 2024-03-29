import pandas as pd
from collections import Counter

def combine_df(df_reco:pd.DataFrame, df_comp:pd.DataFrame):
    """Combine the dataframe of our ratings and the dataframe of ratings, just load them"""
    df_reco_comp = pd.concat([df_reco.iloc[:,:2],df_reco[df_reco.iloc[:,2].name]], axis=1).rename(columns={df_reco.iloc[:,2].name:'rating'}) #
    df_reco_comp['user'] = df_reco.iloc[:,2].name #fill with name
    for col in df_reco.iloc[:,3:]:
        df_temp = pd.concat([df_reco.iloc[:,:2],df_reco[col]], axis=1).rename(columns={col:'rating'})
        df_temp['user'] = col #fill with name
        df_reco_comp = pd.concat([df_reco_comp, df_temp])
    df_reco_comp = df_reco_comp.rename(columns={'id':'item'})

    df_reco_comp = df_reco_comp.query('rating!=0') #filter animes that we dont know from our dataset
    df_reco_comp['rating'] = df_reco_comp.rating.apply(lambda x: 1 if x== -1 else 2) #set the rating scale to 1 or 2 for our dataset
    df_comp['rating'] = df_comp.rating.apply(lambda x: 1 if x<=5 else 2) #set the rating scale to 1 or 2 for the other dataset
    return pd.concat([df_comp,df_reco_comp.loc[:,['user','item','rating']]], ignore_index=True)

def compute_genres_stats(df:pd.DataFrame, df_ref:pd.DataFrame=None) -> dict:
    """Returns a dict with ratio for the genres in the Dataframe"""
    count_genre = {}
    for genre_list in df.Genres_list:
        for genre in genre_list:
            if genre not in count_genre.keys():
                count_genre[genre]=0
            count_genre[genre]+=1
    for genre, count in count_genre.items():
        count_genre[genre] = count/len(df)
    return count_genre

    # alt one-line version
    # return {k:v/len(df) for k,v in dict(Counter([genre for genre_list in df.Genres_list for genre in genre_list])).items()}

def genres_for_playlists(genre_personal:dict, genre_global:dict) -> dict:
    """Returns a dict ordered by the difference between ratios of the presences of genres in two dict.

    First dict should be the dict for which we want to make playlists for."""
    genres_diff = {}
    for genre, ratio in genre_personal.items():
        genres_diff[genre] = ratio-genre_global[genre]
    return dict(sorted(genres_diff.items(), key=lambda x: x[1], reverse=True))

def get_recommendations(user:str, algo, df_users:pd.DataFrame, df_animes:pd.DataFrame, filter_genre:str=None):
    """Get recommendations for a specific user. Needs the user name, the trained algo and a DataFrame with animes"""
    user_inner_uid = algo.trainset.to_inner_uid(user)
    df_rec = pd.DataFrame([algo.trainset.to_raw_uid(x) for x in algo.get_neighbors(user_inner_uid,10)], columns=['user']) #create df with list of nearest users
    df_rec = pd.merge(df_rec, df_users, how='inner', on='user') #merge with df that contain ratings
    df_rec = pd.merge(df_rec, df_animes, how='inner', left_on='item', right_on='MAL_ID') #merge with df that contain animes names
    if filter_genre:
        df_rec = df_rec[df_rec.Genres_list.map(set([filter_genre]).issubset)]
    return pd.merge(df_rec.groupby('item').rating.median().sort_values(ascending=False).head(10), df_animes, how='inner', left_on='item', right_on='MAL_ID') #compute median of ratings by users and select top 10 rated animes

def get_recommendations_v2(user:str, algo, df_full:pd.DataFrame, df_animes:pd.DataFrame, filter_genre:str=None):
    """Get recommendations for a specific user. Needs the user name, the trained algo and a DataFrame with animes
    
    Based on predictions between user and animes rather than between similarity with other users"""
    user_inner_uid = algo.trainset.to_inner_uid(user)
    list_predictions = []
    for anime_id in df_full.query('user!="@user"').item.unique():
        try:
            anime_inner_iid = algo.trainset.to_inner_iid(anime_id)
        except ValueError:
            pass
        list_predictions.append([anime_id, algo.predict(user_inner_uid, anime_inner_iid).est])
    df_rec = pd.merge(pd.DataFrame(list_predictions, columns=['MAL_ID', 'est_rating']), df_animes, how='inner', on='MAL_ID')
    if filter_genre:
        df_rec = df_rec[df_rec.Genres_list.map(set([filter_genre]).issubset)]
    return df_rec.sort_values(by='est_rating', ascending=False).head(10)