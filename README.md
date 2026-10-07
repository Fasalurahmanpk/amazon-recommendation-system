# Personalized Entertainment Recommendation System

A personalized recommendation system for **Movies & TV** and **Video Games** using the Amazon Reviews 2023 dataset.

The project implements and compares multiple recommendation approaches, including collaborative filtering, matrix factorization, content-based recommendation, and a hybrid recommendation system.

---

## Project Overview

Online platforms contain a large number of movies, TV shows, and video games, making it difficult for users to discover relevant content.

This project aims to build a personalized recommendation system that learns from user-item interactions and item metadata to recommend relevant movies and games.

The system explores multiple recommendation techniques and compares their performance using rating prediction and Top-N recommendation metrics.

---

## Dataset

The project uses the **Amazon Reviews 2023** dataset provided by the McAuley Lab.

### Categories

- Movies & TV
- Video Games

### Data Used

- User ratings
- User IDs
- Item IDs
- Timestamps
- Product titles
- Product descriptions
- Categories
- Prices

A **5-core filtering strategy** was applied to retain users and items with sufficient interactions.

---

## Project Pipeline

```text
Amazon Reviews 2023
        │
        ▼
   Data Ingestion
        │
        ▼
    5-Core Filtering
        │
        ▼
 Data Cleaning & Preprocessing
        │
        ▼
   Train/Test Split
        │
        ▼
 Exploratory Data Analysis
        │
        ▼
 ┌─────────────────────────────┐
 │ Recommendation Models       │
 │                             │
 │ User-Based CF               │
 │ Item-Based CF               │
 │ SVD                         │
 │ NMF                         │
 │ Content-Based              │
 │ Hybrid RRF                  │
 └─────────────────────────────┘
        │
        ▼
     Evaluation
        │
        ▼
 Model Comparison & Analysis