# City Opportunity Frontend

React + Vite + TypeScript + Chakra UI frontend for the City Opportunity MVP.

## Quick Start

```bash
npm install
npm run dev
```

## Features

- **City Selection**: Searchable city selector with real-time filtering
- **Industry Scoring**: Client-side opportunity scoring using local data
- **RFP Analysis**: Upload and analyze RFP documents
- **Draft Generation**: Generate draft responses to RFPs

## Configuration

Copy `.env.example` to `.env` and update the API URL if needed:

```bash
cp .env.example .env
```

## Data Files

The app uses local data files in `public/data/`:
- `cities.csv` - City demographic and economic data
- `industries.json` - Industry templates with scoring weights
- `bounds.json` - Normalization bounds for scoring metrics

## Components

- `CitySelect` - Searchable city selector
- `IndustryCard` - Industry opportunity display with scores
- `RequirementsTable` - RFP requirements analysis table
- `DraftBox` - Draft response display with copy functionality

## Pages

- `Home` - City selection and navigation
- `Results` - Industry opportunity scores for selected city
- `Rfp` - RFP analysis and response drafting workflow

## Build

```bash
npm run build
```

The built files will be in the `dist/` directory.