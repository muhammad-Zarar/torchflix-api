import os
import traceback
import logging
from fastapi import FastAPI, Depends, HTTPException, Security, Request
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from moviebox_api import (
    Search, Session, SubjectType, 
    DownloadableMovieFilesDetail, DownloadableTVSeriesFilesDetail,
    Trending, Homepage, MovieDetails, TVSeriesDetails, 
    Recommend, PopularSearch, HotMoviesAndTVSeries
)

app = FastAPI(title="TorchFlix API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

API_KEY = "elijah2909_secret_key"
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def get_api_key(api_key: str = Security(api_key_header)):
    if api_key == API_KEY: return api_key
    raise HTTPException(status_code=403, detail="Invalid API Key. Use elijah2909_secret_key")

session = Session()

@app.get("/", response_class=HTMLResponse)
async def serve_ui():
    # Vercel needs absolute path resolving
    html_path = os.path.join(os.path.dirname(__file__), '..', 'index.html')
    with open(html_path, "r") as f:
        return f.read()

async def _get_target_item(query: str, type: str):
    sub_type = SubjectType.MOVIES if type == "movie" else SubjectType.TV_SERIES
    search = Search(session, query=query, subject_type=sub_type)
    results = await search.get_content_model()
    if not results.items: raise Exception(f"No {type} found for query: {query}")
    return results.first_item

@app.get("/api/search")
async def search_media(query: str, type: str = "all", api_key: str = Depends(get_api_key)):
    try:
        sub_type = SubjectType.ALL
        if type.lower() == "movie": sub_type = SubjectType.MOVIES
        elif type.lower() == "series": sub_type = SubjectType.TV_SERIES
        return await Search(session, query=query, subject_type=sub_type, per_page=15).get_content()
    except Exception as e: return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/trending")
async def get_trending(api_key: str = Depends(get_api_key)):
    try: return await Trending(session).get_content()
    except Exception as e: return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/media-files")
async def get_media_files(query: str, type: str = "movie", season: int = 1, episode: int = 1, api_key: str = Depends(get_api_key)):
    try:
        target_item = await _get_target_item(query, type)
        if type == "movie": details = await DownloadableMovieFilesDetail(session, target_item).get_content_model()
        else: details = await DownloadableTVSeriesFilesDetail(session, target_item).get_content_model(season=season, episode=episode)
        videos = [{"resolution": d.resolution, "url": str(d.url), "size": d.size, "ext": d.ext} for d in details.downloads]
        subs = [{"language": c.lanName, "url": str(c.url), "ext": c.ext} for c in details.captions]
        return {"status": "success", "title": target_item.title, "videos": videos, "subtitles": subs}
    except Exception as e: return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/homepage")
async def get_homepage(api_key: str = Depends(get_api_key)):
    try: return await Homepage(session).get_content()
    except Exception as e: return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/details")
async def get_details(query: str, type: str = "movie", api_key: str = Depends(get_api_key)):
    try:
        target_item = await _get_target_item(query, type)
        if type == "movie": return await MovieDetails(target_item, session).get_content()
        else: return await TVSeriesDetails(target_item, session).get_content()
    except Exception as e: return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/recommendations")
async def get_recommendations(query: str, type: str = "movie", api_key: str = Depends(get_api_key)):
    try: return await Recommend(session, await _get_target_item(query, type)).get_content()
    except Exception as e: return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/popular-searches")
async def get_popular_searches(api_key: str = Depends(get_api_key)):
    try: return await PopularSearch(session).get_content()
    except Exception as e: return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/api/hot")
async def get_hot(api_key: str = Depends(get_api_key)):
    try: return await HotMoviesAndTVSeries(session).get_content()
    except Exception as e: return JSONResponse(status_code=500, content={"error": str(e)})
