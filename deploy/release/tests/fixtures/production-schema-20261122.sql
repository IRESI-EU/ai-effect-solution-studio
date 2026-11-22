--
-- PostgreSQL database dump
--


-- Dumped from database version 16.15
-- Dumped by pg_dump version 16.15

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: audit_events; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.audit_events (
    id character varying NOT NULL,
    actor_user_id character varying,
    action character varying(120) NOT NULL,
    target_type character varying(80) NOT NULL,
    target_id character varying(200),
    details text,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


--
-- Name: deployments; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.deployments (
    id character varying NOT NULL,
    workflow_id character varying NOT NULL,
    solution_id character varying,
    name character varying NOT NULL,
    status character varying,
    is_archived boolean,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    created_by_user_id character varying
);


--
-- Name: operation_contracts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.operation_contracts (
    id character varying NOT NULL,
    service_id character varying NOT NULL,
    operation_identity text NOT NULL,
    runtime_operation_name character varying(150) NOT NULL,
    contract_version character varying(100) NOT NULL,
    schema_version character varying(20) NOT NULL,
    status character varying(30) NOT NULL,
    source_kind character varying(30) NOT NULL,
    source_reference text,
    definition jsonb NOT NULL,
    created_at timestamp with time zone NOT NULL,
    updated_at timestamp with time zone NOT NULL,
    activated_at timestamp with time zone,
    deprecated_at timestamp with time zone,
    withdrawn_at timestamp with time zone,
    CONSTRAINT ck_operation_contracts_schema_version CHECK (((schema_version)::text = '1.0'::text)),
    CONSTRAINT ck_operation_contracts_source_kind CHECK (((source_kind)::text = ANY ((ARRAY['manual'::character varying, 'manifest'::character varying, 'wp3_package'::character varying, 'demo'::character varying])::text[]))),
    CONSTRAINT ck_operation_contracts_status CHECK (((status)::text = ANY ((ARRAY['draft'::character varying, 'active'::character varying, 'deprecated'::character varying, 'withdrawn'::character varying])::text[])))
);


--
-- Name: services; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.services (
    id character varying NOT NULL,
    name character varying(200) NOT NULL,
    provider character varying(200) NOT NULL,
    category character varying(100) NOT NULL,
    status character varying(50) NOT NULL,
    version character varying(50) NOT NULL,
    description text NOT NULL,
    lifecycle_status character varying,
    input_type character varying(100) NOT NULL,
    output_type character varying(100) NOT NULL,
    trust_badge character varying(100) NOT NULL,
    container_name character varying(150) NOT NULL,
    image character varying(250) NOT NULL,
    proto_uri character varying(250) NOT NULL,
    node_type character varying(100) NOT NULL,
    operation_name character varying(150) NOT NULL,
    input_message_name character varying(150) NOT NULL,
    output_message_name character varying(150) NOT NULL,
    internal_host character varying(150) NOT NULL,
    internal_port character varying(20) NOT NULL,
    repository_url text,
    repository_branch character varying,
    manifest_path text,
    interface_type character varying,
    interface_contract jsonb,
    orchestration_mode character varying,
    adapter_type character varying,
    health_path character varying,
    contract_uri text,
    owner_node character varying(40),
    created_by_user_id character varying
);


--
-- Name: solutions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.solutions (
    id character varying NOT NULL,
    name character varying NOT NULL,
    description text,
    nodes jsonb NOT NULL,
    edges jsonb NOT NULL,
    status character varying,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    created_by_user_id character varying
);


--
-- Name: user_sessions; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.user_sessions (
    id character varying NOT NULL,
    user_id character varying NOT NULL,
    token_hash character varying(64) NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    expires_at timestamp without time zone NOT NULL,
    last_seen_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    user_agent character varying(500),
    ip_address character varying(64)
);


--
-- Name: users; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.users (
    id character varying NOT NULL,
    email character varying(320) NOT NULL,
    display_name character varying(160) NOT NULL,
    password_hash text NOT NULL,
    role character varying(40) DEFAULT 'solution_designer'::character varying NOT NULL,
    node character varying(40),
    status character varying(30) DEFAULT 'pending'::character varying NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    approved_at timestamp without time zone,
    approved_by_user_id character varying,
    last_login_at timestamp without time zone,
    CONSTRAINT ck_node_manager_assignment CHECK ((((role)::text <> 'node_manager'::text) OR (node IS NOT NULL))),
    CONSTRAINT ck_users_node CHECK (((node IS NULL) OR ((node)::text = ANY ((ARRAY['germany'::character varying, 'portugal'::character varying, 'denmark'::character varying, 'dutch'::character varying])::text[])))),
    CONSTRAINT ck_users_role CHECK (((role)::text = ANY ((ARRAY['solution_designer'::character varying, 'node_manager'::character varying, 'platform_admin'::character varying])::text[]))),
    CONSTRAINT ck_users_status CHECK (((status)::text = ANY ((ARRAY['pending'::character varying, 'active'::character varying, 'rejected'::character varying, 'suspended'::character varying])::text[])))
);


--
-- Name: audit_events audit_events_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_events
    ADD CONSTRAINT audit_events_pkey PRIMARY KEY (id);


--
-- Name: deployments deployments_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.deployments
    ADD CONSTRAINT deployments_pkey PRIMARY KEY (id);


--
-- Name: operation_contracts operation_contracts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operation_contracts
    ADD CONSTRAINT operation_contracts_pkey PRIMARY KEY (id);


--
-- Name: services services_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.services
    ADD CONSTRAINT services_pkey PRIMARY KEY (id);


--
-- Name: solutions solutions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.solutions
    ADD CONSTRAINT solutions_pkey PRIMARY KEY (id);


--
-- Name: operation_contracts uq_operation_contracts_service_identity_version; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operation_contracts
    ADD CONSTRAINT uq_operation_contracts_service_identity_version UNIQUE (service_id, operation_identity, contract_version);


--
-- Name: user_sessions user_sessions_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_pkey PRIMARY KEY (id);


--
-- Name: user_sessions user_sessions_token_hash_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_token_hash_key UNIQUE (token_hash);


--
-- Name: users users_email_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_email_key UNIQUE (email);


--
-- Name: users users_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_pkey PRIMARY KEY (id);


--
-- Name: ix_audit_events_actor_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_events_actor_user_id ON public.audit_events USING btree (actor_user_id);


--
-- Name: ix_audit_events_created_action; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_audit_events_created_action ON public.audit_events USING btree (created_at, action);


--
-- Name: ix_deployments_created_by_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_deployments_created_by_user_id ON public.deployments USING btree (created_by_user_id);


--
-- Name: ix_deployments_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_deployments_id ON public.deployments USING btree (id);


--
-- Name: ix_deployments_workflow_id; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_deployments_workflow_id ON public.deployments USING btree (workflow_id);


--
-- Name: ix_operation_contracts_service_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_operation_contracts_service_id ON public.operation_contracts USING btree (service_id);


--
-- Name: ix_operation_contracts_service_status; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_operation_contracts_service_status ON public.operation_contracts USING btree (service_id, status);


--
-- Name: ix_services_created_by_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_services_created_by_user_id ON public.services USING btree (created_by_user_id);


--
-- Name: ix_services_owner_node; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_services_owner_node ON public.services USING btree (owner_node);


--
-- Name: ix_solutions_created_by_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_solutions_created_by_user_id ON public.solutions USING btree (created_by_user_id);


--
-- Name: ix_solutions_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_solutions_id ON public.solutions USING btree (id);


--
-- Name: ix_user_sessions_expires_at; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_sessions_expires_at ON public.user_sessions USING btree (expires_at);


--
-- Name: ix_user_sessions_token_hash; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_sessions_token_hash ON public.user_sessions USING btree (token_hash);


--
-- Name: ix_user_sessions_user_id; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_user_sessions_user_id ON public.user_sessions USING btree (user_id);


--
-- Name: ix_users_email; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX ix_users_email ON public.users USING btree (email);


--
-- Name: audit_events audit_events_actor_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.audit_events
    ADD CONSTRAINT audit_events_actor_user_id_fkey FOREIGN KEY (actor_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- Name: deployments deployments_solution_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.deployments
    ADD CONSTRAINT deployments_solution_id_fkey FOREIGN KEY (solution_id) REFERENCES public.solutions(id);


--
-- Name: operation_contracts operation_contracts_service_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.operation_contracts
    ADD CONSTRAINT operation_contracts_service_id_fkey FOREIGN KEY (service_id) REFERENCES public.services(id);


--
-- Name: user_sessions user_sessions_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.user_sessions
    ADD CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES public.users(id) ON DELETE CASCADE;


--
-- Name: users users_approved_by_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.users
    ADD CONSTRAINT users_approved_by_user_id_fkey FOREIGN KEY (approved_by_user_id) REFERENCES public.users(id) ON DELETE SET NULL;


--
-- PostgreSQL database dump complete
--


