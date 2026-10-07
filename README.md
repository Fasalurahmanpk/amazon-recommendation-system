# amazon-recommendation-system
# Amazon Recommendation System

A full-stack personalized recommendation system for **Movies & TV** and **Video Games**, built using the Amazon Reviews 2023 dataset.

The system implements multiple recommendation approaches — **Content-Based Filtering, Collaborative Filtering, Matrix Factorization, and Hybrid Recommendation** — and exposes them through a FastAPI backend with a React + Vite frontend.

> **Note:** The raw Amazon datasets are intentionally excluded from this repository because of their large size. They can be downloaded and processed using the provided scripts.

---

## 🚀 Features

- 🎬 Movie & TV recommendations
- 🎮 Video game recommendations
- 🔎 Item search
- 🧠 Multiple recommendation algorithms
- 🔗 Hybrid recommendation combining multiple signals
- ⚡ FastAPI REST backend
- ⚛️ React + Vite frontend
- 📊 Recommendation evaluation
- 🛡️ API health monitoring
- 🧠 Memory guard for large recommendation models
- 📈 Evaluation reports and visualizations

---

## 🏗️ System Architecture

```text
                    ┌─────────────────────┐
                    │    React + Vite     │
                    │      Frontend       │
                    └──────────┬──────────┘
                               │
                               │ REST API
                               ▼
                    ┌─────────────────────┐
                    │     FastAPI         │
                    │      Backend        │
                    └──────────┬──────────┘
                               │
              ┌────────────────┼────────────────┐
              │                │                │
              ▼                ▼                ▼
       Content-Based      Collaborative      Hybrid
        Filtering          Filtering        Recommendation
              │                │                │
              └────────────────┼────────────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ Processed Dataset   │
                    │ Movies + Games       │
                    └─────────────────────┘
```

---

## 🧠 Recommendation Methods

### 1. Content-Based Filtering

Recommends items based on their characteristics and metadata.

The system analyzes item information such as:

- Title
- Description
- Categories
- Other available metadata

Items with similar characteristics are recommended to the user.

---

### 2. Collaborative Filtering

Uses user-item interaction data to identify patterns in user preferences.

The model recommends items based on similarities between users and their interactions with products.

---

### 3. Matrix Factorization

Matrix factorization decomposes the user-item interaction matrix into lower-dimensional representations.

This allows the system to learn latent user and item preferences and generate personalized recommendations.

---

### 4. Hybrid Recommendation

The hybrid approach combines multiple recommendation signals to improve recommendation quality.

```text
Content-Based Signal
        +
Collaborative Signal
        +
Other Recommendation Signals
        ↓
Hybrid Recommendation
```

---

## 📊 Dataset

This
