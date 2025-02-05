/**
 * Copyright ©2024. The Regents of the University of California (Regents). All Rights Reserved.
 *
 * Permission to use, copy, modify, and distribute this software and its documentation
 * for educational, research, and not-for-profit purposes, without fee and without a
 * signed licensing agreement, is hereby granted, provided that the above copyright
 * notice, this paragraph and the following two paragraphs appear in all copies,
 * modifications, and distributions.
 *
 * Contact The Office of Technology Licensing, UC Berkeley, 2150 Shattuck Avenue,
 * Suite 510, Berkeley, CA 94720-1620, (510) 643-7201, otl@berkeley.edu,
 * http://ipira.berkeley.edu/industry-info for commercial licensing opportunities.
 *
 * IN NO EVENT SHALL REGENTS BE LIABLE TO ANY PARTY FOR DIRECT, INDIRECT, SPECIAL,
 * INCIDENTAL, OR CONSEQUENTIAL DAMAGES, INCLUDING LOST PROFITS, ARISING OUT OF
 * THE USE OF THIS SOFTWARE AND ITS DOCUMENTATION, EVEN IF REGENTS HAS BEEN ADVISED
 * OF THE POSSIBILITY OF SUCH DAMAGE.
 *
 * REGENTS SPECIFICALLY DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
 * IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
 * SOFTWARE AND ACCOMPANYING DOCUMENTATION, IF ANY, PROVIDED HEREUNDER IS PROVIDED
 * "AS IS". REGENTS HAS NO OBLIGATION TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
 * ENHANCEMENTS, OR MODIFICATIONS.
 */

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;
SET row_security = off;
SET search_path = public, pg_catalog;
SET default_tablespace = '';
SET default_with_oids = false;

--

CREATE TYPE job_schedule_types AS ENUM (
    'day_at',
    'minutes',
    'seconds'
);

--

CREATE TABLE canvas_site_mailing_list_members (
    id SERIAL PRIMARY KEY,
    mailing_list_id INTEGER NOT NULL,
    email_address CHARACTER VARYING(255) NOT NULL,
    can_send BOOLEAN DEFAULT FALSE NOT NULL,
    first_name CHARACTER VARYING(255),
    last_name CHARACTER VARYING(255),
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    deleted_at TIMESTAMP WITH TIME ZONE,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL,
    welcomed_at TIMESTAMP WITH TIME ZONE
);
ALTER TABLE ONLY canvas_site_mailing_list_members
    ADD CONSTRAINT canvas_site_mailing_list_members_unique_constraint UNIQUE (mailing_list_id, email_address);
CREATE INDEX canvas_site_mailing_list_members_deleted_at_idx
    ON canvas_site_mailing_list_members USING btree (deleted_at);
CREATE INDEX canvas_site_mailing_list_members_welcomed_at_idx
    ON canvas_site_mailing_list_members USING btree (welcomed_at);

--

CREATE TABLE canvas_site_mailing_lists (
    id SERIAL PRIMARY KEY,
    canvas_site_id INTEGER NOT NULL,
    canvas_site_name CHARACTER VARYING(255),
    list_name CHARACTER VARYING(255),
    members_count INTEGER,
    populate_add_errors INTEGER,
    populate_remove_errors INTEGER,
    populated_at TIMESTAMP WITH TIME ZONE,
    state CHARACTER VARYING(255),
    term_id INTEGER,
    type CHARACTER VARYING(255),
    welcome_email_active BOOLEAN DEFAULT FALSE NOT NULL,
    welcome_email_body TEXT,
    welcome_email_subject TEXT,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
ALTER TABLE ONLY canvas_site_mailing_lists
    ADD CONSTRAINT canvas_site_mailing_lists_unique_constraint UNIQUE (canvas_site_id);
ALTER TABLE ONLY canvas_site_mailing_lists
    ADD CONSTRAINT canvas_site_mailing_lists_name_unique_constraint UNIQUE (list_name);

--

-- This table contains one and only one row.

CREATE TABLE canvas_synchronization (
    id BOOLEAN PRIMARY KEY DEFAULT TRUE,
    last_guest_user_sync TIMESTAMP WITH TIME ZONE,
    latest_term_enrollment_csv_set TIMESTAMP WITH TIME ZONE,
    last_enrollment_sync TIMESTAMP WITH TIME ZONE,
    last_instructor_sync TIMESTAMP WITH TIME ZONE,
    CONSTRAINT canvas_synchronization_unique CHECK (id)
);
ALTER TABLE ONLY canvas_synchronization
    ADD CONSTRAINT canvas_synchronization_unique_constraint CHECK (id);
INSERT INTO canvas_synchronization (id) VALUES (TRUE);

--

-- This table contains one and only one row.

CREATE TABLE configuration (
    id BOOLEAN PRIMARY KEY DEFAULT TRUE,
    hypersleep BOOLEAN NOT NULL DEFAULT FALSE,
    CONSTRAINT configuration_unique_constraint CHECK (id)
);
INSERT INTO configuration (id) VALUES (TRUE);

--

CREATE TABLE job_history (
    id INTEGER NOT NULL,
    job_key VARCHAR(80) NOT NULL,
    failed BOOLEAN DEFAULT FALSE,
    result TEXT,
    started_at TIMESTAMP WITH TIME ZONE NOT NULL,
    finished_at TIMESTAMP WITH TIME ZONE
);
CREATE SEQUENCE job_history_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE job_history_id_seq OWNED BY job_history.id;
ALTER TABLE ONLY job_history ALTER COLUMN id SET DEFAULT nextval('job_history_id_seq'::regclass);
ALTER TABLE ONLY job_history
    ADD CONSTRAINT job_history_pkey PRIMARY KEY (id);

--

CREATE TABLE job_runner (
    ec2_instance_id VARCHAR(80) NOT NULL
);

--

CREATE TABLE jobs (
    id INTEGER NOT NULL,
    disabled BOOLEAN NOT NULL,
    job_schedule_type job_schedule_types NOT NULL,
    job_schedule_value VARCHAR(80) NOT NULL,
    key VARCHAR(80) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL
);
CREATE SEQUENCE jobs_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;
ALTER SEQUENCE jobs_id_seq OWNED BY jobs.id;
ALTER TABLE ONLY jobs ALTER COLUMN id SET DEFAULT nextval('jobs_id_seq'::regclass);
ALTER TABLE ONLY jobs
    ADD CONSTRAINT jobs_pkey PRIMARY KEY (id);
ALTER TABLE ONLY jobs
    ADD CONSTRAINT jobs_key_unique_constraint UNIQUE (key);

--

CREATE TABLE admin_users (
    uid CHARACTER VARYING(255) PRIMARY KEY,
    created_at TIMESTAMP WITH TIME ZONE NOT NULL
);

--

ALTER TABLE ONLY canvas_site_mailing_list_members
    ADD CONSTRAINT canvas_site_mailing_list_members_mailing_list_id_fkey FOREIGN KEY (mailing_list_id) REFERENCES canvas_site_mailing_lists(id) ON DELETE CASCADE;

