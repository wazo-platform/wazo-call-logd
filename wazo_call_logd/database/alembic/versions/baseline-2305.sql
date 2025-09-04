-- PostgreSQL database dump

-- Dumped from database version 13.18 (Debian 13.18-0+deb11u1)
-- Dumped by pg_dump version 13.18 (Debian 13.18-0+deb11u1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

-- Name: call_logd_call_log_participant_role; Type: TYPE; Schema: public; Owner: -

CREATE TYPE public.call_logd_call_log_participant_role AS ENUM (
    'source',
    'destination'
);

SET default_tablespace = '';

SET default_table_access_method = heap;

-- Name: call_logd_call_log; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.call_logd_call_log (
    id integer NOT NULL,
    date timestamp with time zone NOT NULL,
    date_answer timestamp with time zone,
    date_end timestamp with time zone,
    tenant_uuid uuid NOT NULL,
    source_name character varying(255),
    source_exten character varying(255),
    source_internal_exten text,
    source_internal_context text,
    source_line_identity character varying(255),
    requested_name text,
    requested_exten character varying(255),
    requested_context character varying(255),
    requested_internal_exten text,
    requested_internal_context text,
    destination_name character varying(255),
    destination_exten character varying(255),
    destination_internal_exten text,
    destination_internal_context text,
    destination_line_identity character varying(255),
    direction character varying(255),
    user_field character varying(255),
    source_internal_name text,
    CONSTRAINT call_logd_call_log_direction_check CHECK (direction IN ('inbound', 'internal', 'outbound'))
);

-- Name: call_logd_call_log_destination; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.call_logd_call_log_destination (
    uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    destination_details_key character varying(32) NOT NULL,
    destination_details_value character varying(255) NOT NULL,
    call_log_id integer,
    CONSTRAINT call_logd_call_log_destination_details_key_check CHECK (destination_details_key IN ('type', 'user_uuid', 'user_name', 'meeting_uuid', 'meeting_name', 'conference_id'))
);

-- Name: call_logd_call_log_id_seq; Type: SEQUENCE; Schema: public; Owner: -

CREATE SEQUENCE public.call_logd_call_log_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: call_logd_call_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -

ALTER SEQUENCE public.call_logd_call_log_id_seq OWNED BY public.call_logd_call_log.id;

-- Name: call_logd_call_log_participant; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.call_logd_call_log_participant (
    uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    call_log_id integer,
    user_uuid uuid NOT NULL,
    line_id integer,
    role public.call_logd_call_log_participant_role NOT NULL,
    tags character varying(128)[] DEFAULT '{}'::character varying[] NOT NULL,
    answered boolean DEFAULT false NOT NULL
);

-- Name: call_logd_config; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.call_logd_config (
    id integer NOT NULL,
    retention_cdr_days integer,
    retention_cdr_days_from_file boolean NOT NULL,
    retention_recording_days integer,
    retention_recording_days_from_file boolean NOT NULL,
    retention_export_days integer,
    retention_export_days_from_file boolean NOT NULL
);

-- Name: call_logd_config_id_seq; Type: SEQUENCE; Schema: public; Owner: -

CREATE SEQUENCE public.call_logd_config_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;

-- Name: call_logd_config_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -

ALTER SEQUENCE public.call_logd_config_id_seq OWNED BY public.call_logd_config.id;

-- Name: call_logd_export; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.call_logd_export (
    uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    tenant_uuid uuid NOT NULL,
    user_uuid uuid NOT NULL,
    requested_at timestamp with time zone NOT NULL,
    status character varying(32) NOT NULL,
    path text,
    CONSTRAINT call_logd_export_status_check CHECK (status IN ('pending', 'processing', 'finished', 'deleted', 'error'))
);

-- Name: call_logd_recording; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.call_logd_recording (
    uuid uuid DEFAULT public.uuid_generate_v4() NOT NULL,
    start_time timestamp with time zone NOT NULL,
    end_time timestamp with time zone NOT NULL,
    path text,
    call_log_id integer NOT NULL
);

-- Name: call_logd_retention; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.call_logd_retention (
    tenant_uuid uuid NOT NULL,
    cdr_days integer,
    recording_days integer,
    export_days integer
);

-- Name: call_logd_tenant; Type: TABLE; Schema: public; Owner: -

CREATE TABLE public.call_logd_tenant (
    uuid uuid NOT NULL
);

-- Name: call_logd_call_log id; Type: DEFAULT; Schema: public; Owner: -

ALTER TABLE ONLY public.call_logd_call_log ALTER COLUMN id SET DEFAULT nextval('public.call_logd_call_log_id_seq'::regclass);

-- Name: call_logd_config id; Type: DEFAULT; Schema: public; Owner: -

ALTER TABLE ONLY public.call_logd_config ALTER COLUMN id SET DEFAULT nextval('public.call_logd_config_id_seq'::regclass);

-- Data for Name: call_logd_call_log; Type: TABLE DATA; Schema: public; Owner: -

-- Data for Name: call_logd_call_log_destination; Type: TABLE DATA; Schema: public; Owner: -

-- Data for Name: call_logd_call_log_participant; Type: TABLE DATA; Schema: public; Owner: -

-- Data for Name: call_logd_config; Type: TABLE DATA; Schema: public; Owner: -

-- Data for Name: call_logd_export; Type: TABLE DATA; Schema: public; Owner: -

-- Data for Name: call_logd_recording; Type: TABLE DATA; Schema: public; Owner: -

-- Data for Name: call_logd_retention; Type: TABLE DATA; Schema: public; Owner: -

-- Data for Name: call_logd_tenant; Type: TABLE DATA; Schema: public; Owner: -

-- Name: call_logd_call_log_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -

SELECT pg_catalog.setval('public.call_logd_call_log_id_seq', 1, false);

-- Name: call_logd_config_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -

SELECT pg_catalog.setval('public.call_logd_config_id_seq', 1, false);

-- Name: call_logd_call_log_destination call_logd_call_log_destination_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.call_logd_call_log_destination
    ADD CONSTRAINT call_logd_call_log_destination_pkey PRIMARY KEY (uuid);

-- Name: call_logd_call_log_participant call_logd_call_log_participant_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.call_logd_call_log_participant
    ADD CONSTRAINT call_logd_call_log_participant_pkey PRIMARY KEY (uuid);

-- Name: call_logd_call_log call_logd_call_log_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.call_logd_call_log
    ADD CONSTRAINT call_logd_call_log_pkey PRIMARY KEY (id);

-- Name: call_logd_config call_logd_config_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.call_logd_config
    ADD CONSTRAINT call_logd_config_pkey PRIMARY KEY (id);

-- Name: call_logd_export call_logd_export_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.call_logd_export
    ADD CONSTRAINT call_logd_export_pkey PRIMARY KEY (uuid);

-- Name: call_logd_recording call_logd_recording_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.call_logd_recording
    ADD CONSTRAINT call_logd_recording_pkey PRIMARY KEY (uuid);

-- Name: call_logd_tenant call_logd_tenant_pkey; Type: CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.call_logd_tenant
    ADD CONSTRAINT call_logd_tenant_pkey PRIMARY KEY (uuid);

-- Name: call_logd_call_log_destination__idx__uuid; Type: INDEX; Schema: public; Owner: -

CREATE INDEX call_logd_call_log_destination__idx__uuid ON public.call_logd_call_log_destination USING btree (uuid);

-- Name: call_logd_call_log_participant__idx__call_log_id; Type: INDEX; Schema: public; Owner: -

CREATE INDEX call_logd_call_log_participant__idx__call_log_id ON public.call_logd_call_log_participant USING btree (call_log_id);

-- Name: call_logd_call_log_participant__idx__user_uuid; Type: INDEX; Schema: public; Owner: -

CREATE INDEX call_logd_call_log_participant__idx__user_uuid ON public.call_logd_call_log_participant USING btree (user_uuid);

-- Name: call_logd_export__idx__user_uuid; Type: INDEX; Schema: public; Owner: -

CREATE INDEX call_logd_export__idx__user_uuid ON public.call_logd_export USING btree (user_uuid);

-- Name: call_logd_call_log_destination call_logd_call_log_destination_call_log_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.call_logd_call_log_destination
    ADD CONSTRAINT call_logd_call_log_destination_call_log_id_fkey FOREIGN KEY (call_log_id) REFERENCES public.call_logd_call_log(id) ON DELETE CASCADE;

-- Name: call_logd_call_log_participant call_logd_call_log_participant_call_log_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.call_logd_call_log_participant
    ADD CONSTRAINT call_logd_call_log_participant_call_log_id_fkey FOREIGN KEY (call_log_id) REFERENCES public.call_logd_call_log(id) ON DELETE CASCADE;

-- Name: call_logd_call_log call_logd_call_log_tenant_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.call_logd_call_log
    ADD CONSTRAINT call_logd_call_log_tenant_uuid_fkey FOREIGN KEY (tenant_uuid) REFERENCES public.call_logd_tenant(uuid) ON DELETE CASCADE;

-- Name: call_logd_export call_logd_export_tenant_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.call_logd_export
    ADD CONSTRAINT call_logd_export_tenant_uuid_fkey FOREIGN KEY (tenant_uuid) REFERENCES public.call_logd_tenant(uuid) ON DELETE CASCADE;

-- Name: call_logd_recording call_logd_recording_call_log_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.call_logd_recording
    ADD CONSTRAINT call_logd_recording_call_log_id_fkey FOREIGN KEY (call_log_id) REFERENCES public.call_logd_call_log(id) ON DELETE CASCADE;

-- Name: call_logd_retention call_logd_retention_tenant_uuid_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -

ALTER TABLE ONLY public.call_logd_retention
    ADD CONSTRAINT call_logd_retention_tenant_uuid_fkey FOREIGN KEY (tenant_uuid) REFERENCES public.call_logd_tenant(uuid) ON DELETE CASCADE;

-- PostgreSQL database dump complete
