# %%
import os
import time

import numpy as np
import pandas as pd
import requests

cwd = os.getcwd()
movies_df = pd.read_csv(cwd + '/data/movies.csv')
links_df = pd.read_csv(cwd + '/data/links.csv')

if os.path.isfile(cwd + '/data//movies_enrichment.csv'):
    movies_enrichment_df = pd.read_csv(cwd + '/../data_big/movies_enrichment.csv')
else:
    movies_enrichment_df = None

API_TOKEN = '<my_api_token>'

FETCH_MOVIE_ROUTE = 'https://api.themoviedb.org/3/movie'

movies_with_tmdb_ids = movies_df.merge(links_df, how='left', on='movieId').dropna()
movies_with_tmdb_ids['tmdbId'] = movies_with_tmdb_ids['tmdbId'].astype('int32')

# Chunk DF
n = 50  # chunk size
start = 30000
movies_as_chunk = [movies_with_tmdb_ids[i:i + n] for i in range(start, movies_with_tmdb_ids.shape[0], n)]


def tmdb_movie(tmdb_movie_id, lens_movie_id):
    headers = {
        'Content-Type': "application/json",
        'Authorization': f"Bearer {API_TOKEN}"
    }

    url = f'{FETCH_MOVIE_ROUTE}/{tmdb_movie_id}'
    print(f'URL : {url} // LENS_ID : {lens_movie_id}')

    try:
        r = requests.get(url, headers=headers)
        r.raise_for_status()

        movie_json = r.json()  # dict

        tmdb_budget = movie_json['budget'] if movie_json['budget'] > 0 else np.nan
        revenue = movie_json['revenue'] if movie_json['revenue'] > 0 else np.nan
        vote_average = movie_json['vote_average'] if movie_json['vote_average'] > 0 else np.nan
        vote_count = movie_json['vote_count'] if movie_json['vote_count'] > 0 else np.nan

        production_companies_names = '|'.join(
            [companie['name'] for companie in movie_json['production_companies']]
        )
        production_companies_countries = '|'.join(
            [country['iso_3166_1'] for country in movie_json['production_countries']]
        )
        poster_path = movie_json['poster_path'] \
            if movie_json['poster_path'] is not None and len(movie_json['poster_path']) > 0 \
            else np.nan

        return tmdb_budget, revenue, vote_average, vote_count, \
               production_companies_names, production_companies_countries, poster_path

    except Exception as error:
        print(f'Error during request. Response code was : {r.status_code}. TMDB Movie ID was : {tmdb_movie_id}')
        print('An exception occurred: {}'.format(error))

        return None


# If there are already some data, we use it instead of override it
if movies_enrichment_df is not None:
    movies_df_copy = movies_enrichment_df.copy()
else:
    movies_df_copy = movies_df.copy()

    # Fill expected columns with NaN in case there are missing values from TMDB
    nan_serie = pd.Series([np.nan] * movies_df_copy.shape[0])
    movies_df_copy['tmdb_budget'] = nan_serie
    movies_df_copy['tmdb_revenue'] = nan_serie
    movies_df_copy['tmdb_vote_avg'] = nan_serie
    movies_df_copy['tmdb_vote_count'] = nan_serie
    movies_df_copy['tmdb_companie_name'] = nan_serie
    movies_df_copy['tmdb_companie_iso'] = nan_serie
    movies_df_copy['tmdb_poster_path'] = nan_serie

for idx, movies in enumerate(movies_as_chunk):
    # Reset index to 0,1,2, etc.
    movies = movies.reset_index(drop=True)
    start_movie_id = movies.loc[0, 'movieId']
    print(f'========================= >> Start of chunk #{idx} with movie ID #{start_movie_id}' + '\n\n')

    for row in movies.itertuples():
        (index, movieId, title, genres, imdbId, tmdbId) = row

        # Retrieve the values from site ....
        results = tmdb_movie(tmdbId, movieId)
        if results is not None:
            (budget, revenue, vote_avg, vote_count, prod_companie_name, prod_companie_country, poster_path) = results
            print(budget, revenue, vote_avg, vote_count, prod_companie_name, prod_companie_country, poster_path)
            print('')
            # Unpack values and set them to corresponding columns :
            movies_df_copy.loc[movies_df_copy.movieId == movieId,
                               ['tmdb_budget', 'tmdb_revenue', 'tmdb_vote_avg', 'tmdb_vote_count',
                                'tmdb_companie_name', 'tmdb_companie_iso', 'tmdb_poster_path']] = \
                (budget, revenue, vote_avg, vote_count, prod_companie_name, prod_companie_country, poster_path)

    movies_df_copy.to_csv(f'{os.getcwd()}/data/movies_enrichment.csv', index=False)

    end_movie_id = movies.loc[movies.shape[0] - 1, 'movieId']
    print(f'<< ========================= End of chunk #{idx} with movie ID #{end_movie_id}. \n '
          f'Now sleeping 1.5 second...' + '\n\n')
    time.sleep(1.5)
