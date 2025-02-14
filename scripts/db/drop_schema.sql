/**
 * Copyright ©2025. The Regents of the University of California (Regents). All Rights Reserved.
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

--

ALTER TABLE IF EXISTS ONLY public.canvas_site_mailing_list_members
    DROP CONSTRAINT IF EXISTS canvas_site_mailing_list_members_unique_constraint;
ALTER TABLE IF EXISTS ONLY public.canvas_site_mailing_list_members
    DROP CONSTRAINT IF EXISTS canvas_site_mailing_list_members_mailing_list_id_fkey;
ALTER TABLE IF EXISTS ONLY public.canvas_site_mailing_lists
    DROP CONSTRAINT IF EXISTS canvas_site_mailing_lists_unique_constraint;
ALTER TABLE IF EXISTS ONLY public.canvas_site_mailing_lists
    DROP CONSTRAINT IF EXISTS canvas_site_mailing_lists_name_unique_constraint;
ALTER TABLE IF EXISTS ONLY public.canvas_synchronization
    DROP CONSTRAINT IF EXISTS canvas_synchronization_unique_constraint;
ALTER TABLE IF EXISTS ONLY public.configuration
    DROP CONSTRAINT IF EXISTS configuration_unique_constraint;
ALTER TABLE IF EXISTS ONLY public.jobs
    DROP CONSTRAINT IF EXISTS jobs_key_unique_constraint;
ALTER TABLE IF EXISTS ONLY public.jobs
    DROP CONSTRAINT IF EXISTS jobs_pkey;

--

DROP INDEX IF EXISTS public.canvas_site_mailing_list_members_deleted_at_idx;
DROP INDEX IF EXISTS public.canvas_site_mailing_list_members_welcomed_at_idx;

--

DROP TABLE IF EXISTS public.canvas_site_mailing_list_members;
DROP TABLE IF EXISTS public.canvas_site_mailing_lists;
DROP TABLE IF EXISTS public.canvas_synchronization;
DROP TABLE IF EXISTS public.configuration;
DROP TABLE IF EXISTS public.job_history;
DROP SEQUENCE IF EXISTS job_history_id_seq;
DROP TABLE IF EXISTS public.jobs;
DROP TABLE IF EXISTS public.job_runner;
DROP SEQUENCE IF EXISTS jobs_id_seq;
DROP TABLE IF EXISTS public.admin_users;

--

DROP TYPE IF EXISTS public.job_schedule_types;

--

