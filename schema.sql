-- ─────────────────────────────────────────────────────────────
-- Schéma CRM Vignerons Indépendants
-- À exécuter dans : Supabase → SQL Editor → New Query
-- ─────────────────────────────────────────────────────────────

CREATE TABLE IF NOT EXISTS vignerons (
    id                        UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    slug                      TEXT UNIQUE NOT NULL,

    -- Données scraper (listing)
    nom                       TEXT,
    region                    TEXT,
    appellation               TEXT,
    commune                   TEXT,
    code_postal               TEXT,
    departement               TEXT,
    adresse_complete          TEXT,
    couleurs                  TEXT,
    nb_vins                   INTEGER,
    a_email                   BOOLEAN DEFAULT FALSE,
    latitude                  DOUBLE PRECISION,
    longitude                 DOUBLE PRECISION,
    url_fiche                 TEXT,

    -- Coordonnées (scraping fiche détail)
    telephone                 TEXT,
    telephone_mobile          TEXT,
    email                     TEXT,
    site_web                  TEXT,
    facebook                  TEXT,
    instagram                 TEXT,
    description               TEXT,
    details_scrapped_at       TIMESTAMPTZ,

    -- CRM
    statut                    TEXT DEFAULT 'prospect'
                              CHECK (statut IN ('prospect','contacté','à relancer','refus','signé')),
    derniere_interaction_at   TIMESTAMPTZ,
    derniere_interaction_type TEXT,

    -- Méta
    created_at                TIMESTAMPTZ DEFAULT NOW(),
    updated_at                TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS interactions (
    id          UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    vigneron_id UUID NOT NULL REFERENCES vignerons(id) ON DELETE CASCADE,
    type        TEXT CHECK (type IN ('appel','email','visite','message','autre')),
    date        TIMESTAMPTZ DEFAULT NOW(),
    notes       TEXT,
    auteur      TEXT,
    created_at  TIMESTAMPTZ DEFAULT NOW()
);

-- Index performances
CREATE INDEX IF NOT EXISTS idx_vignerons_statut  ON vignerons(statut);
CREATE INDEX IF NOT EXISTS idx_vignerons_region  ON vignerons(region);
CREATE INDEX IF NOT EXISTS idx_inter_vigneron    ON interactions(vigneron_id);
CREATE INDEX IF NOT EXISTS idx_inter_date        ON interactions(date DESC);

-- Trigger updated_at auto
CREATE OR REPLACE FUNCTION _set_updated_at()
RETURNS TRIGGER LANGUAGE plpgsql AS $$
BEGIN NEW.updated_at = NOW(); RETURN NEW; END;
$$;

DROP TRIGGER IF EXISTS vignerons_updated_at ON vignerons;
CREATE TRIGGER vignerons_updated_at
    BEFORE UPDATE ON vignerons
    FOR EACH ROW EXECUTE FUNCTION _set_updated_at();
