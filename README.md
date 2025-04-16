
# EcoCart

Smart Grocery Planning Platform  
Built with Django + DRF + PostgreSQL + Docker

EcoCart is a full-featured grocery planning and price comparison backend system. It enables users to manage collaborative shopping lists, compare product prices from different suppliers, and receive intelligent product recommendations based on their shopping history.

---

## Features

- JWT Authentication with social login (Google, Facebook, Apple ID)
- Shopping List Management (CRUD operations)
- Real-Time Shared Shopping Lists via WebSocket
- Price Comparison Engine between suppliers
- Discount & Loyalty Program (EcoPoints)
- Personalized Product Recommendations
- Product Expiry Tracking System
- Supplier & Admin Dashboards

---

## Tech Stack

- Backend: Django, Django REST Framework (DRF)
- Database: PostgreSQL
- Authentication: JWT, Django Allauth (OAuth2)
- Real-Time: Django Channels (WebSocket)
- DevOps: Docker
- Frontend (Planned): Vue 3 / React

---

## Main Models

- User – Custom user model (extended from AbstractUser)
- Product, Category
- Supplier – Connected to user
- ProductSupplier – Links products to suppliers with price & stock info
- Discount – Applied to products/suppliers
- ShoppingList, ShoppingItem
- Recommendation – Based on shopping history

---

## Highlights

- WebSocket support for collaborative list editing
- Price comparison logic based on supplier offers
- JWT authentication with refresh tokens
- Modular architecture suitable for microservices
- Clean and scalable project structure

---

## Getting Started

```bash
# Clone the repository
git clone https://github.com/nurzat04/EcoCart.git
cd EcoCart

# Run with Docker
docker-compose up --build