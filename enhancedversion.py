from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
from datetime import datetime

app = FastAPI(title="Enhanced Movie Booking System", version="2.0")

# Enhanced Request Models
class MovieCreate(BaseModel):
    title: str = Field(..., min_length=1, description="Movie title")
    duration_minutes: int = Field(..., gt=0, description="Duration in minutes")
    genre: str = Field(..., min_length=1, description="Movie genre")
    description: Optional[str] = Field(None, description="Movie description")
    rating: Optional[str] = Field(None, description="Movie rating (G, PG, PG-13, R)")

class ShowtimeCreate(BaseModel):
    movie_id: int = Field(..., description="Movie ID")
    start_time: datetime = Field(..., description="Show start time")
    price: float = Field(..., gt=0, description="Ticket price")
    total_seats: int = Field(50, ge=10, le=500, description="Total seats available")

class BookingCreate(BaseModel):
    showtime_id: int = Field(..., description="Showtime ID")
    customer_name: str = Field(..., min_length=1, description="Customer name")
    customer_email: Optional[str] = Field(None, description="Customer email")
    customer_phone: Optional[str] = Field(None, description="Customer phone")
    seats_booked: int = Field(..., gt=0, description="Number of seats to book")

# Enhanced Response Models
class Movie(MovieCreate):
    id: int
    created_at: datetime = Field(default_factory=datetime.now)

class ShowtimeResponse(BaseModel):
    id: int
    movie_id: int
    movie_title: str  # Include movie title in response
    start_time: datetime
    price: float
    total_seats: int
    available_seats: int
    booked_seats: int
    occupancy_percentage: float  # Calculated field
    status: str  # "Available", "Nearly Full", "Sold Out"

class BookingResponse(BaseModel):
    id: int
    showtime_id: int
    movie_title: str
    showtime: datetime
    customer_name: str
    customer_email: Optional[str]
    customer_phone: Optional[str]
    seats_booked: int
    price_per_seat: float
    total_amount: float
    booking_time: datetime
    remaining_seats_after_booking: int
    booking_status: str  # "Confirmed", "Cancelled"

class ShowtimeAvailability(BaseModel):
    showtime_id: int
    movie_title: str
    start_time: datetime
    price: float
    available_seats: int
    total_seats: int
    occupancy_percentage: float
    status: str

# Storage
movies: Dict[int, Movie] = {}
showtimes: Dict[int, ShowtimeResponse] = {}
bookings: Dict[int, BookingResponse] = {}

movie_counter = 1
showtime_counter = 1
booking_counter = 1

# Helper functions
def calculate_showtime_status(available_seats: int, total_seats: int) -> str:
    occupancy = ((total_seats - available_seats) / total_seats) * 100
    if available_seats == 0:
        return "Sold Out"
    elif occupancy >= 80:
        return "Nearly Full"
    else:
        return "Available"

def get_occupancy_percentage(available_seats: int, total_seats: int) -> float:
    return round(((total_seats - available_seats) / total_seats) * 100, 2)

# API Endpoints
@app.get("/movies", response_model=List[Movie])
def get_movies():
    """Get all movies"""
    return list(movies.values())

@app.post("/movies", response_model=Movie, status_code=201)
def add_movie(movie: MovieCreate):
    """Create a new movie"""
    global movie_counter
    new_movie = Movie(id=movie_counter, **movie.dict())
    movies[movie_counter] = new_movie
    movie_counter += 1
    return new_movie

@app.get("/movies/{movie_id}/showtimes", response_model=List[ShowtimeResponse])
def get_showtimes(movie_id: int):
    """Get all showtimes for a specific movie with availability details"""
    if movie_id not in movies:
        raise HTTPException(status_code=404, detail="Movie not found")
    
    movie_showtimes = [s for s in showtimes.values() if s.movie_id == movie_id]
    return movie_showtimes

@app.get("/showtimes/availability", response_model=List[ShowtimeAvailability])
def get_all_showtimes_availability():
    """Get availability for all showtimes"""
    availability_list = []
    for showtime in showtimes.values():
        movie = movies[showtime.movie_id]
        availability = ShowtimeAvailability(
            showtime_id=showtime.id,
            movie_title=movie.title,
            start_time=showtime.start_time,
            price=showtime.price,
            available_seats=showtime.available_seats,
            total_seats=showtime.total_seats,
            occupancy_percentage=showtime.occupancy_percentage,
            status=showtime.status
        )
        availability_list.append(availability)
    return availability_list

@app.post("/showtimes", response_model=ShowtimeResponse, status_code=201)
def add_showtime(showtime: ShowtimeCreate):
    """Create a new showtime"""
    global showtime_counter
    if showtime.movie_id not in movies:
        raise HTTPException(status_code=404, detail="Movie not found")
    
    movie = movies[showtime.movie_id]
    new_showtime = ShowtimeResponse(
        id=showtime_counter,
        movie_title=movie.title,
        available_seats=showtime.total_seats,
        booked_seats=0,
        occupancy_percentage=0.0,
        status="Available",
        **showtime.dict()
    )
    showtimes[showtime_counter] = new_showtime
    showtime_counter += 1
    return new_showtime

@app.post("/bookings", response_model=BookingResponse, status_code=201)
def book_tickets(booking: BookingCreate):
    """Book tickets with detailed response showing seat availability"""
    global booking_counter
    
    if booking.showtime_id not in showtimes:
        raise HTTPException(status_code=404, detail="Showtime not found")
    
    showtime = showtimes[booking.showtime_id]
    movie = movies[showtime.movie_id]
    
    if booking.seats_booked > showtime.available_seats:
        raise HTTPException(
            status_code=400, 
            detail=f"Not enough seats available. Only {showtime.available_seats} seats remaining."
        )

    # Calculate booking details
    total_amount = booking.seats_booked * showtime.price
    remaining_seats = showtime.available_seats - booking.seats_booked
    
    # Create booking response
    new_booking = BookingResponse(
        id=booking_counter,
        movie_title=movie.title,
        showtime=showtime.start_time,
        price_per_seat=showtime.price,
        total_amount=total_amount,
        booking_time=datetime.now(),
        remaining_seats_after_booking=remaining_seats,
        booking_status="Confirmed",
        **booking.dict()
    )
    
    # Update showtime availability
    showtime.available_seats = remaining_seats
    showtime.booked_seats += booking.seats_booked
    showtime.occupancy_percentage = get_occupancy_percentage(
        showtime.available_seats, showtime.total_seats
    )
    showtime.status = calculate_showtime_status(
        showtime.available_seats, showtime.total_seats
    )
    
    bookings[booking_counter] = new_booking
    booking_counter += 1
    
    return new_booking

@app.get("/bookings/{booking_id}", response_model=BookingResponse)
def get_booking(booking_id: int):
    """Get booking details"""
    if booking_id not in bookings:
        raise HTTPException(status_code=404, detail="Booking not found")
    return bookings[booking_id]

@app.get("/bookings", response_model=List[BookingResponse])
def get_all_bookings():
    """Get all bookings"""
    return list(bookings.values())

@app.delete("/bookings/{booking_id}")
def cancel_booking(booking_id: int):
    """Cancel a booking and return seats to availability"""
    if booking_id not in bookings:
        raise HTTPException(status_code=404, detail="Booking not found")
    
    booking = bookings[booking_id]
    showtime = showtimes[booking.showtime_id]
    
    # Return seats to showtime
    showtime.available_seats += booking.seats_booked
    showtime.booked_seats -= booking.seats_booked
    showtime.occupancy_percentage = get_occupancy_percentage(
        showtime.available_seats, showtime.total_seats
    )
    showtime.status = calculate_showtime_status(
        showtime.available_seats, showtime.total_seats
    )
    
    # Mark booking as cancelled
    booking.booking_status = "Cancelled"
    
    return {
        "message": "Booking cancelled successfully",
        "booking_id": booking_id,
        "seats_returned": booking.seats_booked,
        "showtime_available_seats": showtime.available_seats,
        "showtime_status": showtime.status
    }

# Example usage:
"""
# 1. Create a movie with enhanced details
movie_data = {
    "title": "Avatar: The Way of Water",
    "duration_minutes": 192,
    "genre": "Sci-Fi",
    "description": "Set more than a decade after the events of the first film...",
    "rating": "PG-13"
}

# 2. Create showtime with custom seating
showtime_data = {
    "movie_id": 1,
    "start_time": "2024-12-25T19:30:00",
    "price": 15.99,
    "total_seats": 100
}

# 3. Book tickets (will show detailed response)
booking_data = {
    "showtime_id": 1,
    "customer_name": "John Doe",
    "customer_email": "john@email.com",
    "customer_phone": "+1234567890",
    "seats_booked": 4
}

# Response will include:
# - Movie title and showtime details
# - Seats booked and remaining seats
# - Total amount and per-seat price
# - Occupancy percentage and status
# - Booking confirmation details
"""