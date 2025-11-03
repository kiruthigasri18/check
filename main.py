from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict
from datetime import datetime

app = FastAPI(title="Movie Booking System", version="1.0")

class MovieCreate(BaseModel):
    title: str = Field(..., min_length=1)
    duration_minutes: int = Field(..., gt=0)
    genre: str = Field(..., min_length=1)

class Movie(MovieCreate):
    id: int

class ShowtimeCreate(BaseModel):
    movie_id: int
    start_time: datetime
    price: float = Field(..., gt=0)

class Showtime(ShowtimeCreate):
    id: int
    available_seats: int = 50

class BookingCreate(BaseModel):
    showtime_id: int
    customer_name: str = Field(..., min_length=1)
    seats_booked: int = Field(..., gt=0)

class Booking(BaseModel):
    id: int
    showtime_id: int
    customer_name: str
    seats_booked: int
    total_amount: float

movies: Dict[int, Movie] = {}
showtimes: Dict[int, Showtime] = {}
bookings: Dict[int, Booking] = {}

movie_counter = 1
showtime_counter = 1
booking_counter = 1


@app.get("/movies", response_model=List[Movie])
def get_movies():
    return list(movies.values())


@app.post("/movies", response_model=Movie, status_code=201)
def add_movie(movie: MovieCreate):
    global movie_counter
    new_movie = Movie(id=movie_counter, **movie.dict())
    movies[movie_counter] = new_movie
    movie_counter += 1
    return new_movie


@app.get("/movies/{movie_id}/showtimes", response_model=List[Showtime])
def get_showtimes(movie_id: int):
    if movie_id not in movies:
        raise HTTPException(status_code=404, detail="Movie not found")
    return [s for s in showtimes.values() if s.movie_id == movie_id]


@app.post("/showtimes", response_model=Showtime, status_code=201)
def add_showtime(showtime: ShowtimeCreate):
    global showtime_counter
    if showtime.movie_id not in movies:
        raise HTTPException(status_code=404, detail="Movie not found")
    new_showtime = Showtime(id=showtime_counter, available_seats=50, **showtime.dict())
    showtimes[showtime_counter] = new_showtime
    showtime_counter += 1
    return new_showtime


@app.post("/bookings", response_model=Booking, status_code=201)
def book_tickets(booking: BookingCreate):
    global booking_counter
    if booking.showtime_id not in showtimes:
        raise HTTPException(status_code=404, detail="Showtime not found")
    
    showtime = showtimes[booking.showtime_id]
    if booking.seats_booked > showtime.available_seats:
        raise HTTPException(status_code=400, detail="Not enough seats available")

    total_amount = booking.seats_booked * showtime.price
    new_booking = Booking(
        id=booking_counter,
        total_amount=total_amount,
        **booking.dict()
    )
    bookings[booking_counter] = new_booking
    showtime.available_seats -= booking.seats_booked
    booking_counter += 1
    return new_booking


@app.get("/bookings/{booking_id}", response_model=Booking)
def get_booking(booking_id: int):
    if booking_id not in bookings:
        raise HTTPException(status_code=404, detail="Booking not found")
    return bookings[booking_id]


@app.delete("/bookings/{booking_id}", response_model=dict)
def cancel_booking(booking_id: int):
    if booking_id not in bookings:
        raise HTTPException(status_code=404, detail="Booking not found")
    booking = bookings.pop(booking_id)
    # return seats to showtime
    showtime = showtimes[booking.showtime_id]
    showtime.available_seats += booking.seats_booked
    return {"message": "Booking cancelled successfully"}