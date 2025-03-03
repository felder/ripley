DROP SCHEMA IF EXISTS sis_data cascade;

CREATE SCHEMA sis_data;

CREATE TABLE sis_data.basic_attributes
(
    ldap_uid VARCHAR,
    sid VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    email_address VARCHAR,
    affiliations VARCHAR,
    person_type VARCHAR
);

INSERT INTO sis_data.basic_attributes
(ldap_uid, sid, first_name, last_name, email_address, affiliations, person_type)
VALUES
('10000', '30010000', 'Ellen', 'Ripley', 'ellen.ripley@berkeley.edu', 'EMPLOYEE-TYPE-ACADEMIC', 'S'),
('10001', '30010001', 'Dallas', '👨‍✈️', 'dallas@berkeley.edu', 'EMPLOYEE-TYPE-STAFF', 'S'),
('20000', '30020000', 'Joan', 'Lambert', 'joan.lambert@berkeley.edu', 'STUDENT-TYPE-REGISTERED', 'S'),
('30000', '30030000', 'Ash', '🤖', 'synthetic.ash@berkeley.edu', 'STUDENT-TYPE-NOT REGISTERED', 'S'),
('40000', '30040000', 'XO', 'Kane', 'xo.kane@berkeley.edu', 'STUDENT-TYPE-REGISTERED', 'S'),
('50000', '30050000', 'Dennis', 'Parker', 'dennis.parker@berkeley.edu', 'STUDENT-TYPE-REGISTERED', 'S'),
('60000', '30060000', 'Samuel', 'Brett', 'sam.brett@berkeley.edu', 'STUDENT-TYPE-REGISTERED', 'S'),
('80000', '30080000', 'Jonesie', 'the Cat', 'jonesie@berkeley.edu', 'EMPLOYEE-TYPE-STAFF', 'S');

CREATE TABLE sis_data.edo_enrollment_updates
(
    sis_term_id VARCHAR,
    sis_section_id VARCHAR,
    ldap_uid VARCHAR,
    sis_id VARCHAR,
    sis_enrollment_status VARCHAR,
    course_career VARCHAR,
    last_updated VARCHAR
);

INSERT INTO sis_data.edo_enrollment_updates
(sis_term_id, sis_section_id, ldap_uid, sis_id, sis_enrollment_status, course_career, last_updated)
VALUES
('2232', '32936', '20000', '30020000', 'E', 'UGRD', now()),
('2232', '32936', '40000', '30040000', 'E', 'UGRD', now()),
('2232', '32937', '20000', '30020000', 'E', 'UGRD', now()),
('2232', '32937', '50000', '30050000', 'E', 'UGRD', now()),
('2232', '32937', '60000', '30060000', 'W', 'UGRD', now());

CREATE TABLE sis_data.edo_instructor_updates
(
    sis_term_id VARCHAR,
    sis_course_id VARCHAR,
    sis_section_id VARCHAR,
    ldap_uid VARCHAR,
    sis_id VARCHAR,
    role_code VARCHAR,
    is_primary BOOLEAN,
    last_updated VARCHAR
);

INSERT INTO sis_data.edo_instructor_updates
(sis_term_id, sis_section_id, ldap_uid, sis_id, role_code, is_primary, last_updated)
VALUES
('2232', '32936', '30000', '30030000', 'PI', TRUE, now());

CREATE TABLE sis_data.edo_enrollments
(
    sis_term_id VARCHAR,
    sis_section_id VARCHAR,
    ldap_uid VARCHAR,
    sis_enrollment_status VARCHAR,
    grade VARCHAR,
    grading_basis VARCHAR
);

INSERT INTO sis_data.edo_enrollments
(sis_term_id, sis_section_id, ldap_uid, sis_enrollment_status, grade, grading_basis)
VALUES
('2208', '30300', '1000001', 'E', 'A', 'GRD'),
('2225', '10000', '1000001', 'E', 'P', 'EPN'),
('2225', '10000', '1000002', 'E', 'P', 'EPN'),
('2225', '10000', '1000003', 'E', 'P', 'EPN'),
('2225', '10000', '1000004', 'E', 'P', 'EPN'),
('2225', '10000', '1000005', 'E', 'P', 'EPN'),
('2225', '10000', '1000006', 'E', 'P', 'EPN'),
('2225', '10000', '1000007', 'E', 'P', 'EPN'),
('2225', '10000', '1000008', 'E', 'P', 'EPN'),
('2225', '10000', '1000009', 'E', 'P', 'EPN'),
('2225', '20000', '1000006', 'E', 'P', 'EPN'),
('2225', '20000', '1000007', 'E', 'P', 'EPN'),
('2225', '20000', '1000008', 'E', 'P', 'EPN'),
('2225', '20000', '1000009', 'E', 'A-', 'EPN'),
('2225', '20000', '1000010', 'E', 'C', 'EPN'),
('2225', '20000', '1000011', 'E', 'D', 'EPN'),
('2228', '99999', '1000001', 'E', 'A+', 'GRD'),
('2228', '99999', '1000002', 'E', 'P', 'EPN'),
('2228', '99999', '1000003', 'E', 'A', 'GRD'),
('2228', '99999', '1000004', 'E', 'A', 'GRD'),
('2228', '99999', '1000005', 'E', 'P', 'EPN'),
('2228', '99999', '1000006', 'E', 'P', 'EPN'),
('2228', '99999', '1000007', 'E', 'F', 'GRD'),
('2228', '99999', '1000008', 'E', 'A+', 'GRD'),
('2228', '99999', '1000009', 'E', 'P', 'EPN'),
('2228', '99999', '1000010', 'E', 'A-', 'GRD'),
('2228', '99999', '1000011', 'E', 'A', 'GRD'),
('2228', '99999', '1000012', 'E', 'A', 'GRD'),
('2228', '99999', '1000013', 'E', 'P', 'EPN'),
('2228', '99999', '1000014', 'E', 'A', 'GRD'),
('2228', '99999', '1000015', 'E', 'A+', 'GRD'),
('2228', '99999', '1000016', 'E', 'A', 'GRD'),
('2228', '99999', '1000017', 'E', 'A', 'GRD'),
('2228', '99999', '1000018', 'E', 'A', 'GRD'),
('2228', '99999', '1000019', 'E', 'A', 'GRD'),
('2228', '99999', '1000020', 'E', 'A', 'GRD'),
('2228', '99999', '1000021', 'E', 'A+', 'GRD'),
('2228', '99999', '1000022', 'E', 'A', 'GRD'),
('2228', '99999', '1000023', 'E', 'A', 'GRD'),
('2228', '99999', '1000024', 'E', 'A+', 'GRD'),
('2228', '99999', '1000025', 'E', 'A', 'GRD'),
('2228', '99999', '1000026', 'E', 'A+', 'GRD'),
('2228', '99999', '1000027', 'E', 'A', 'GRD'),
('2228', '99999', '1000028', 'E', 'P', 'EPN'),
('2228', '99999', '1000029', 'E', 'B+', 'GRD'),
('2228', '99999', '1000030', 'E', 'A+', 'GRD'),
('2228', '99999', '1000031', 'E', 'A', 'GRD'),
('2228', '99999', '1000032', 'E', 'A+', 'GRD'),
('2228', '99999', '1000033', 'E', 'A-', 'GRD'),
('2228', '99999', '1000034', 'E', 'A', 'GRD'),
('2228', '99999', '1000035', 'E', 'A', 'GRD'),
('2228', '99999', '1000036', 'E', 'P', 'EPN'),
('2228', '99999', '1000037', 'E', 'A', 'GRD'),
('2228', '99999', '1000038', 'E', 'A', 'GRD'),
('2228', '99999', '1000039', 'E', 'A', 'GRD'),
('2228', '99999', '1000040', 'E', 'A+', 'GRD'),
('2228', '99999', '1000041', 'E', 'B+', 'GRD'),
('2228', '99999', '1000042', 'E', 'A', 'GRD'),
('2228', '99999', '1000043', 'E', 'A', 'GRD'),
('2228', '99999', '1000044', 'E', 'A', 'GRD'),
('2228', '99999', '1000045', 'E', 'A', 'GRD'),
('2228', '99999', '1000046', 'E', 'A+', 'GRD'),
('2228', '99999', '1000047', 'E', 'A', 'GRD'),
('2228', '99999', '1000048', 'E', 'A', 'GRD'),
('2228', '99999', '1000049', 'E', 'A+', 'GRD'),
('2228', '99999', '1000050', 'E', 'A+', 'GRD'),
('2228', '99999', '1000051', 'E', 'A', 'GRD'),
('2228', '99999', '1000052', 'E', 'A', 'GRD'),
('2228', '99999', '1000053', 'E', 'A', 'GRD'),
('2228', '99999', '1000054', 'E', 'A', 'GRD'),
('2228', '99999', '1000055', 'E', 'P', 'EPN'),
('2228', '99999', '1000056', 'E', 'A+', 'GRD'),
('2228', '99999', '1000057', 'E', 'A', 'GRD'),
('2228', '99999', '1000058', 'E', 'A-', 'GRD'),
('2228', '99999', '1000059', 'E', 'A', 'GRD'),
('2228', '99999', '1000060', 'E', 'A', 'GRD'),
('2228', '99999', '1000061', 'E', 'A', 'GRD'),
('2228', '99999', '1000062', 'E', 'A', 'GRD'),
('2228', '99999', '1000063', 'E', 'A', 'GRD'),
('2228', '99999', '1000064', 'E', 'A', 'GRD'),
('2228', '99999', '1000065', 'E', 'A', 'GRD'),
('2228', '99999', '1000066', 'E', 'A', 'GRD'),
('2228', '99999', '1000067', 'E', 'A', 'GRD'),
('2228', '99999', '1000068', 'E', 'A', 'GRD'),
('2228', '99999', '1000069', 'E', 'A', 'GRD'),
('2228', '99999', '1000070', 'E', 'B+', 'GRD'),
('2228', '99999', '1000071', 'E', 'A-', 'GRD'),
('2228', '99999', '1000072', 'E', 'B+', 'GRD'),
('2228', '99999', '1000073', 'E', 'C+', 'GRD'),
('2228', '99999', '1000074', 'E', 'A-', 'GRD'),
('2228', '99999', '1000075', 'E', 'A', 'GRD'),
('2228', '99999', '1000076', 'E', 'A', 'GRD'),
('2228', '99999', '1000077', 'E', 'A', 'GRD'),
('2228', '99999', '1000078', 'E', 'A', 'GRD'),
('2228', '99999', '1000079', 'E', 'B+', 'GRD'),
('2228', '99999', '1000080', 'E', 'A-', 'GRD'),
('2228', '99999', '1000081', 'E', 'A-', 'GRD'),
('2228', '99999', '1000082', 'E', 'A-', 'GRD'),
('2228', '99999', '1000083', 'E', 'A+', 'GRD'),
('2228', '99999', '1000084', 'E', 'A+', 'GRD'),
('2228', '99999', '1000085', 'E', 'A', 'GRD'),
('2228', '99999', '1000086', 'E', 'A', 'GRD'),
('2228', '99999', '1000087', 'E', 'A', 'GRD'),
('2228', '99999', '1000088', 'E', 'A', 'GRD'),
('2228', '99999', '1000089', 'E', 'A', 'GRD'),
('2228', '99999', '1000090', 'E', 'A+', 'GRD'),
('2228', '99999', '1000091', 'E', 'A', 'GRD'),
('2228', '99999', '20000', 'E', 'B', 'GRD'),
('2232', '32936', '20000', 'E', 'B+', 'GRD'),
('2232', '32936', '40000', 'E', 'A', 'GRD'),
('2232', '32937', '20000', 'E', NULL, 'GRD'),
('2232', '32937', '50000', 'E', NULL, 'GRD'),
('2232', '32937', '60000', 'W', NULL, 'GRD'),
('2232', '32937', '1000006', 'W', 'A+', 'GRD'),
('2232', '32937', '1000007', 'W', 'A', 'GRD'),
('2232', '32937', '1000008', 'W', 'A-', 'GRD'),
('2232', '32937', '1000009', 'W', 'B+', 'GRD'),
('2232', '32937', '1000010', 'W', 'B', 'GRD'),
('2228', '17276', '1000010', 'W', 'B', 'GRD');

CREATE TABLE sis_data.edo_sections (
    sis_term_id VARCHAR,
    sis_section_id VARCHAR,
    is_primary BOOLEAN,
    dept_name VARCHAR,
    sis_course_name VARCHAR,
    sis_course_title VARCHAR,
    sis_instruction_format VARCHAR,
    sis_section_num VARCHAR,
    allowed_units NUMERIC,
    cs_course_id VARCHAR,
    session_code VARCHAR,
    instruction_mode VARCHAR,
    primary_associated_section_id VARCHAR,
    instructor_uid VARCHAR,
    instructor_name VARCHAR,
    instructor_role_code VARCHAR,
    meeting_location VARCHAR,
    meeting_days VARCHAR,
    meeting_start_time VARCHAR,
    meeting_end_time VARCHAR,
    meeting_start_date VARCHAR,
    meeting_end_date VARCHAR
);

INSERT INTO sis_data.edo_sections
(sis_term_id, sis_section_id, is_primary, dept_name, sis_course_name, sis_course_title, sis_instruction_format, sis_section_num, allowed_units, cs_course_id, session_code, instruction_mode, primary_associated_section_id, instructor_uid, instructor_name, instructor_role_code, meeting_location, meeting_days, meeting_start_time, meeting_end_time, meeting_start_date, meeting_end_date)
VALUES
('2232', '32936', TRUE, 'ANTHRO', 'ANTHRO 189', 'Our Dogs, Ourselves: Encounters between the Human and the Non-Human', 'LEC', '001', NULL, '876543', 1, 'P', NULL, '30000', 'Ash 🤖', 'PI', NULL, NULL, NULL, NULL, NULL, NULL),
('2232', '32936', TRUE, 'ANTHRO', 'ANTHRO 189', 'Our Dogs, Ourselves: Encounters between the Human and the Non-Human', 'LEC', '001', NULL, '876543', 1, 'P', NULL, '50000', 'Denis Parker', 'TNIC', NULL, NULL, NULL, NULL, NULL, NULL),
('2232', '32937', TRUE, 'ANTHRO', 'ANTHRO 189', 'Our Dogs, Ourselves: Encounters between the Human and the Non-Human', 'LEC', '002', NULL, '876543', 1, 'P', NULL, '30000', 'Ash 🤖', 'PI', NULL, NULL, NULL, NULL, NULL, NULL),
('2225', '10000', TRUE, 'ANTHRO', 'ANTHRO 197', 'Fieldwork', 'FLD', '001', NULL, '100726', 1, 'P', NULL, '13579', 'Fitzi Ritz', 'PI', NULL, NULL, NULL, NULL, NULL, NULL),
('2228', '17275', TRUE, 'ANTHRO', 'ANTHRO 197', 'Fieldwork', 'FLD', '001', NULL, '100726', 1, 'P', NULL, '13579', 'Fitzi Ritz', 'PI', NULL, NULL, NULL, NULL, NULL, NULL),
('2228', '17276', TRUE, 'ANTHRO', 'ANTHRO 197', 'Fieldwork', 'FLD', '001', NULL, '100726', 1, 'P', NULL, '30000', 'Ash', 'PI', NULL, NULL, NULL, NULL, NULL, NULL),
('2228', '17277', TRUE, 'ANTHRO', 'ANTHRO 197', 'Fieldwork', 'FLD', '002', NULL, '100726', 1, 'P', NULL, '200122', 'Mufty Blauswater', 'PI', NULL, NULL, NULL, NULL, NULL, NULL),
('2225', '20000', TRUE, 'ASTRON', 'ASTRON 218', 'Stellar Dynamics and Galactic Structure', 'LEC', '001', NULL, '1234567', 1, 'P', NULL, '30000', 'Ash', 'PI', 'Sevastopol Station', 'SAMOWE', '09:00', '11:00', '2023-02-17', '2023-02-17'),
('2232', '12345', TRUE, 'ASTRON', 'ASTRON 218', 'Stellar Dynamics and Galactic Structure', 'LEC', '001', NULL, '1234567', 1, 'P', NULL, '30000', 'Ash', 'PI', 'Sevastopol Station', 'SAMOWE', '09:00', '11:00', '2023-02-17', '2023-02-17'),
('2232', '12347', FALSE, 'ASTRON', 'ASTRON 218', 'Stellar Dynamics and Galactic Structure', 'DIS', '101', NULL, '1234567', 1, 'P', '12345', '200122', 'Mufty Blauswater', 'PI', 'Sevastopol Station', 'TU', '14:00', '15:00', '2023-01-17', '2023-05-17'),
('2232', '12346', TRUE, 'ASTRON', 'ASTRON 218', 'Stellar Dynamics and Galactic Structure', 'LEC', '002', NULL, '1234567', 1, 'P', NULL, '30000', 'Ash', 'PI', 'Acheron LV 426', 'TUTH', '09:00', '13:30', '2023-01-17', '2023-05-05'),
('2232', '12346', TRUE, 'ASTRON', 'ASTRON 218', 'Stellar Dynamics and Galactic Structure', 'LEC', '002', NULL, '1234567', 1, 'P', NULL, '13579', 'Fitzi Ritz', 'PI', 'Acheron LV 426', 'TUTH', '09:00', '13:30', '2023-01-17', '2023-05-05'),
('2228', '32290', TRUE, 'ASTRON', 'ASTRON C228', 'Extragalactic Astronomy and Cosmology', 'LEC', '001', NULL, '124009', 1, 'P', NULL, '30000', 'Ash', 'PI', NULL, NULL, NULL, NULL, NULL, NULL),
('2228', '32291', TRUE, 'ASTRON', 'ASTRON C228', 'Extragalactic Astronomy and Cosmology', 'LEC', '002', NULL, '124009', 1, 'P', NULL, '30000', 'Ash', 'PI', NULL, NULL, NULL, NULL, NULL, NULL),
('2228', '99999', TRUE, 'ASTRON', 'ASTRON 218', 'Stellar Dynamics and Galactic Structure', 'LEC', '001', NULL, '2345678', 1, 'P', NULL, '30000', 'Ash', 'PI', NULL, NULL, NULL, NULL, NULL, NULL),
('2208', '30300', TRUE, 'ASTRON', 'ASTRON 3', 'Introduction to Modern Cosmology', 'LEC', '001', NULL, '3456789', 1, 'P', NULL, '30000', 'Ash', 'APRX', NULL, NULL, NULL, NULL, NULL, NULL);

DROP SCHEMA IF EXISTS student cascade;

CREATE SCHEMA student;

CREATE TABLE student.demographics
(
    sid VARCHAR,
    gender VARCHAR,
    minority BOOLEAN
);

INSERT INTO student.demographics
(sid, gender, minority)
VALUES
('3000000001','Female',TRUE),
('3000000002','Female',TRUE),
('3000000003','Male',TRUE),
('3000000004','Male',FALSE),
('3000000005','Male',FALSE),
('3000000006','Male',FALSE),
('3000000007','Female',TRUE),
('3000000008','Female',FALSE),
('3000000009','Female',TRUE),
('3000000010','Female',FALSE),
('3000000011','Female',TRUE),
('3000000012','Female',TRUE),
('3000000013','Female',TRUE),
('3000000014','Female',FALSE),
('3000000015','Female',FALSE),
('3000000016','Male',TRUE),
('3000000017','Female',FALSE),
('3000000018','Female',FALSE),
('3000000019','Female',TRUE),
('3000000020','Female',FALSE),
('3000000021','Female',TRUE),
('3000000022','Female',TRUE),
('3000000023','Female',TRUE),
('3000000024','Male',TRUE),
('3000000025','Male',FALSE),
('3000000026','Male',TRUE),
('3000000027','Male',FALSE),
('3000000028','Female',FALSE),
('3000000029','Female',TRUE),
('3000000030','Female',FALSE),
('3000000031','Male',FALSE),
('3000000032','Female',TRUE),
('3000000033','Female',FALSE),
('3000000034','Male',TRUE),
('3000000035','Male',TRUE),
('3000000036','Female',TRUE),
('3000000037','Female',TRUE),
('3000000038','Female',FALSE),
('3000000039','Female',TRUE),
('3000000040','Male',TRUE),
('3000000041','Genderqueer/Gender Non-Conform',TRUE),
('3000000042','Female',TRUE),
('3000000043','Female',TRUE),
('3000000044','Female',TRUE),
('3000000045','Male',FALSE),
('3000000046','Female',FALSE),
('3000000047','Female',TRUE),
('3000000048','Female',TRUE),
('3000000049','Female',TRUE),
('3000000050','Female',FALSE),
('3000000051','Female',TRUE),
('3000000052','Female',FALSE),
('3000000053','Female',TRUE),
('3000000054','Female',TRUE),
('3000000055','Male',TRUE),
('3000000056','Female',TRUE),
('3000000057','Female',FALSE),
('3000000058','Female',TRUE),
('3000000059','Female',TRUE),
('3000000060','Female',FALSE),
('3000000061','Male',FALSE),
('3000000062','Female',TRUE),
('3000000063','Female',TRUE),
('3000000064','Male',TRUE),
('3000000065','Female',TRUE),
('3000000066','Male',TRUE),
('3000000067','Male',TRUE),
('3000000068','Female',TRUE),
('3000000069','Male',TRUE),
('3000000070','Female',TRUE),
('3000000071','Female',FALSE),
('3000000072','Female',FALSE),
('3000000073','Female',TRUE),
('3000000074','Female',FALSE),
('3000000075','Female',FALSE),
('3000000076','Female',TRUE),
('3000000077','Female',TRUE),
('3000000078','Female',TRUE),
('3000000079','Female',FALSE),
('3000000080','Female',TRUE),
('3000000081','Male',FALSE),
('3000000082','Male',FALSE),
('3000000083','Female',TRUE),
('3000000084','Female',TRUE),
('3000000085','Female',FALSE),
('3000000086','Female',TRUE),
('3000000087','Female',FALSE),
('3000000088','Female',FALSE),
('3000000089','Female',FALSE),
('3000000090','Female',TRUE),
('3000000091','Female',FALSE);

CREATE TABLE student.ethnicities
(
    sid VARCHAR,
    ethnicity VARCHAR
);

INSERT INTO student.ethnicities
(sid, ethnicity)
VALUES
('3000000001','Mexican / Mexican-American / Chicano'),
('3000000002','Mexican / Mexican-American / Chicano'),
('3000000003','Mexican / Mexican-American / Chicano'),
('3000000004','White'),
('3000000005','White'),
('3000000006','White'),
('3000000007','Mexican / Mexican-American / Chicano'),
('3000000008','White'),
('3000000009','Mexican / Mexican-American / Chicano'),
('3000000010','White'),
('3000000011','Mexican / Mexican-American / Chicano'),
('3000000012','Other Spanish-American / Latino'),
('3000000013','Mexican / Mexican-American / Chicano'),
('3000000014','White'),
('3000000015','White'),
('3000000016','Mexican / Mexican-American / Chicano'),
('3000000017','Not Specified'),
('3000000018','Chinese / Chinese-American'),
('3000000019','Mexican / Mexican-American / Chicano'),
('3000000020','White'),
('3000000021','Mexican / Mexican-American / Chicano'),
('3000000022','Mexican / Mexican-American / Chicano'),
('3000000023','Mexican / Mexican-American / Chicano'),
('3000000024','Mexican / Mexican-American / Chicano'),
('3000000025','White'),
('3000000026','Other Spanish-American / Latino'),
('3000000027','White'),
('3000000028','Chinese / Chinese-American'),
('3000000029','Mexican / Mexican-American / Chicano'),
('3000000030','White'),
('3000000031','Japanese / Japanese American'),
('3000000032','Mexican / Mexican-American / Chicano'),
('3000000033','White'),
('3000000034','Other Spanish-American / Latino'),
('3000000035','Other Spanish-American / Latino'),
('3000000036','Mexican / Mexican-American / Chicano'),
('3000000037','Mexican / Mexican-American / Chicano'),
('3000000038','White'),
('3000000039','Mexican / Mexican-American / Chicano'),
('3000000040','Puerto Rican'),
('3000000041','Other Spanish-American / Latino'),
('3000000042','Other Spanish-American / Latino'),
('3000000043','Mexican / Mexican-American / Chicano'),
('3000000044','Mexican / Mexican-American / Chicano'),
('3000000045','Chinese / Chinese-American'),
('3000000045','Vietnamese'),
('3000000046','White'),
('3000000047','Puerto Rican'),
('3000000048','Mexican / Mexican-American / Chicano'),
('3000000049','Mexican / Mexican-American / Chicano'),
('3000000050','White'),
('3000000051','Mexican / Mexican-American / Chicano'),
('3000000052','White'),
('3000000053','Mexican / Mexican-American / Chicano'),
('3000000054','Mexican / Mexican-American / Chicano'),
('3000000055','Mexican / Mexican-American / Chicano'),
('3000000056','Mexican / Mexican-American / Chicano'),
('3000000057','White'),
('3000000058','Mexican / Mexican-American / Chicano'),
('3000000059','Mexican / Mexican-American / Chicano'),
('3000000060','Vietnamese'),
('3000000061','East Indian / Pakistani'),
('3000000062','Other Spanish-American / Latino'),
('3000000063','Chinese / Chinese-American'),
('3000000063','Other Spanish-American / Latino'),
('3000000064','Mexican / Mexican-American / Chicano'),
('3000000065','Mexican / Mexican-American / Chicano'),
('3000000066','Other Spanish-American / Latino'),
('3000000067','Mexican / Mexican-American / Chicano'),
('3000000068','Mexican / Mexican-American / Chicano'),
('3000000069','Mexican / Mexican-American / Chicano'),
('3000000070','Other Spanish-American / Latino'),
('3000000071','White'),
('3000000072','White'),
('3000000073','Mexican / Mexican-American / Chicano'),
('3000000074','Not Specified'),
('3000000075','White'),
('3000000076','Other Spanish-American / Latino'),
('3000000077','Other Spanish-American / Latino'),
('3000000078','Mexican / Mexican-American / Chicano'),
('3000000079','White'),
('3000000080','Mexican / Mexican-American / Chicano'),
('3000000081','Chinese / Chinese-American'),
('3000000082','White'),
('3000000083','Mexican / Mexican-American / Chicano'),
('3000000084','Mexican / Mexican-American / Chicano'),
('3000000085','White'),
('3000000086','Other Spanish-American / Latino'),
('3000000087','White'),
('3000000088','Korean / Korean-American'),
('3000000089','Chinese / Chinese-American'),
('3000000090','Mexican / Mexican-American / Chicano'),
('3000000091','Chinese / Chinese-American');

CREATE TABLE student.student_profile_index
(
    sid VARCHAR,
    uid VARCHAR,
    first_name VARCHAR,
    last_name VARCHAR,
    level VARCHAR,
    gpa DECIMAL(5,3),
    units DECIMAL(6,3),
    transfer BOOLEAN,
    expected_grad_term VARCHAR(4),
    terms_in_attendance INTEGER,
    email_address VARCHAR,
    entering_term VARCHAR(4),
    academic_career_status VARCHAR
);

INSERT INTO student.student_profile_index
(sid, uid, first_name, last_name, level, gpa, units, transfer, expected_grad_term, terms_in_attendance, email_address, entering_term, academic_career_status)
VALUES
('30040000','40000','Thomas','Kane','GR','3.5','120',FALSE,'2252','12','xo.kane@berkeley.edu','2208','active'),
('3000000009','1000075','First','Last','20','3.232','53.76',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000003','1000091','First','Last','40','3.872','102.36',TRUE,'2242','7','oski@berkeley.edu','2228','active'),
('3000000053','1000016','First','Last','40','3.608','118.12',FALSE,'2242','7','oski@berkeley.edu','2208','active'),
('3000000046','1000067','First','Last','20','3.75','56',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000054','1000030','First','Last','20','2.886','57',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000063','1000084','First','Last','30','3.836','68.12',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000047','1000051','First','Last','20','3.01','55.76',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000055','1000021','First','Last','30','3.58','86.8',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000083','1000083','First','Last','30','3.96','60.12',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000028','1000013','First','Last','40','3.726','103.76',FALSE,'2242','7','oski@berkeley.edu','2208','active'),
('3000000080','1000009','First','Last','40','3.961','136.5',FALSE,'2232','8','oski@berkeley.edu','2198','completed'),
('3000000048','1000015','First','Last','30','3.647','74.04',FALSE,'2242','5','oski@berkeley.edu','2208','active'),
('3000000072','1000033','First','Last','30','3.353','73.9',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000087','1000064','First','Last','40','3.908','98.16',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000065','1000031','First','Last','30','2.94','66.86',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000091','1000004','First','Last','40','3.93','135.92',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000090','1000024','First','Last','40','3.167','117.08',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000033','1000052','First','Last','30','4','60.16',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000045','1000001','First','Last','40','3.968','156.52',FALSE,'2232','8','oski@berkeley.edu','2198','completed'),
('3000000075','1000063','First','Last','30','3.656','83.4',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000060','1000041','First','Last','30','3.782','76.52',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000001','1000010','First','Last','40','3.128','151.72',FALSE,'2232','8','oski@berkeley.edu','2198','active'),
('3000000042','1000027','First','Last','40','3.868','90.12',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000036','1000085','First','Last','30','3.547','63.08',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000041','1000076','First','Last','30','3.961','70.16',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000034','1000072','First','Last','30','2.404','66.72',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000070','1000078','First','Last','30','3.892','63.84',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000025','1000005','First','Last','40','4','121.2',FALSE,'2242','7','oski@berkeley.edu','2208','active'),
('3000000031','1000049','First','Last','30','4','60.84',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000005','1000006','First','Last','40','3.889','168.88',FALSE,'2232','8','oski@berkeley.edu','2198','active'),
('3000000050','1000065','First','Last','40','3.726','132.6',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000006','1000089','First','Last','30','4','71.52',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000073','1000079','First','Last','20','3.194','39.72',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000027','1000034','First','Last','30','3.878','76.72',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000044','1000088','First','Last','20','3.519','46.08',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000064','1000081','First','Last','20','3.216','57.81',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000071','1000086','First','Last','30','3.762','70.54',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000023','1000026','First','Last','30','3.627','85.84',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000069','1000043','First','Last','20','3.416','56.76',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000057','1000060','First','Last','30','3.647','66.5',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000030','1000002','First','Last','40','3.737','135.22',FALSE,'2232','8','oski@berkeley.edu','2198','completed'),
('3000000052','1000042','First','Last','20','3.553','41.36',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000015','1000018','First','Last','40','3.238','144.52',FALSE,'2242','7','oski@berkeley.edu','2208','active'),
('3000000088','1000046','First','Last','30','4','74.2',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000089','1000062','First','Last','40','3.387','105.88',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000076','1000014','First','Last','40','3.922','166.72',FALSE,'2242','7','oski@berkeley.edu','2208','active'),
('3000000037','1000023','First','Last','40','3.793','94.48',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000082','1000036','First','Last','20','3.83','45.08',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000062','1000037','First','Last','20','2.6','33.72',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000002','1000032','First','Last','40','3.774','110.72',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000085','1000020','First','Last','30','3.456','76.76',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000067','1000073','First','Last','40','1.806','109.52',TRUE,'2238','8','oski@berkeley.edu','2218','active'),
('3000000032','1000090','First','Last','20','3.785','59.12',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000013','1000074','First','Last','40','3.269','134.08',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000021','1000003','First','Last','40','3.925','145.48',FALSE,'2232','8','oski@berkeley.edu','2198','active'),
('3000000049','1000029','First','Last','30','2.47','75.36',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000077','1000058','First','Last','40','2.711','98.12',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000017','1000080','First','Last','30','3.742','66.84',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000018','1000008','First','Last','40','3.924','175.56',FALSE,'2232','8','oski@berkeley.edu','2198','completed'),
('3000000026','1000057','First','Last','30','3.738','88.04',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000014','1000017','First','Last','40','3.85','96.9',FALSE,'2242','7','oski@berkeley.edu','2208','active'),
('3000000038','1000039','First','Last','30','3.884','62.48',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000051','1000012','First','Last','40','3.573','159',FALSE,'2242','7','oski@berkeley.edu','2208','active'),
('3000000011','1000070','First','Last','30','3.342','74.4',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000008','1000061','First','Last','30','3.244','80.8',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000019','1000044','First','Last','30','4','63.12',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000010','1000022','First','Last','40','3.951','102.16',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000066','1000040','First','Last','30','3.947','86.3',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000079','1000028','First','Last','40','3.954','99.2',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000016','1000071','First','Last','40','2.72','99.84',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000035','1000082','First','Last','20','3.214','33.36',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000040','1000068','First','Last','30','3.718','87.72',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000056','1000025','First','Last','30','3.25','66.72',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000039','1000054','First','Last','30','4','79',TRUE,'2242','6','oski@berkeley.edu','2228','active'),
('3000000029','1000066','First','Last','30','3.705','81.08',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000061','1000050','First','Last','30','4','68.08',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000024','1000038','First','Last','20','3.543','36.36',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000007','1000053','First','Last','40','3.911','105.36',TRUE,'2248','7','oski@berkeley.edu','2228','active'),
('3000000043','1000048','First','Last','30','3.293','65.44',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000058','1000087','First','Last','30','3.3','74.72',FALSE,'2248','3','oski@berkeley.edu','2228','active'),
('3000000084','1000045','First','Last','30','2.426','67.16',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000078','1000047','First','Last','30','3.56','60.48',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000074','1000056','First','Last','30','4','32',FALSE,'','5','oski@berkeley.edu','','active'),
('3000000012','1000077','First','Last','20','3.245','40.36',FALSE,'2262','3','oski@berkeley.edu','2228','active'),
('3000000086','1000069','First','Last','30','3.587','89.48',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000020','1000059','First','Last','40','3.767','99.52',FALSE,'2252','5','oski@berkeley.edu','2218','active'),
('3000000004','1000007','First','Last','30','1.808','72.12',FALSE,'2238','8','oski@berkeley.edu','2198','active'),
('3000000022','1000011','First','Last','40','3.513','162.44',FALSE,'2232','8','oski@berkeley.edu','2198','completed'),
('3000000059','1000035','First','Last','20','2.268','59.8',FALSE,'2252','3','oski@berkeley.edu','2218','active'),
('3000000068','1000055','First','Last','40','3.637','90.08',TRUE,'2242','7','oski@berkeley.edu','2228','active'),
('3000000081','1000019','First','Last','40','3.795','93.16',FALSE,'2242','5','oski@berkeley.edu','2208','active');

CREATE TABLE student.visas
(
    sid VARCHAR,
    visa_status VARCHAR,
    visa_type VARCHAR
);

INSERT INTO student.visas
(sid, visa_status, visa_type)
VALUES
('3000000004','G','OT'),
('3000000018','A','PR'),
('3000000011','A','RF'),
('3000000012','G','PR'),
('3000000035','A','PR'),
('3000000083','G','PR'),
('3000000007','G','PR'),
('3000000062','G','PR'),
('3000000024','A','PA'),
('3000000074','G','J1'),
('3000000051','G','PR'),
('3000000053','A','PR'),
('3000000091','G','PR'),
('3000000090','A','PR'),
('3000000034','A','F1'),
('3000000009','A','OT');

DROP SCHEMA IF EXISTS terms cascade;

CREATE SCHEMA terms;

CREATE TABLE terms.term_definitions
(
    term_id VARCHAR(4) NOT NULL,
    term_name VARCHAR NOT NULL,
    term_begins DATE NOT NULL,
    term_ends DATE NOT NULL
);

INSERT INTO terms.term_definitions
(term_id, term_name, term_begins, term_ends)
VALUES
('2102','Spring 2010','2010-01-12','2010-05-14'),
('2105','Summer 2010','2010-05-24','2010-08-13'),
('2108','Fall 2010','2010-08-19','2010-12-17'),
('2112','Spring 2011','2011-01-11','2011-05-13'),
('2115','Summer 2011','2011-05-23','2011-08-12'),
('2118','Fall 2011','2011-08-18','2011-12-16'),
('2122','Spring 2012','2012-01-10','2012-05-11'),
('2125','Summer 2012','2012-05-21','2012-08-10'),
('2128','Fall 2012','2012-08-16','2012-12-14'),
('2132','Spring 2013','2013-01-15','2013-05-17'),
('2135','Summer 2013','2013-05-28','2013-08-16'),
('2138','Fall 2013','2013-08-22','2013-12-20'),
('2142','Spring 2014','2014-01-14','2014-05-16'),
('2145','Summer 2014','2014-05-27','2014-08-15'),
('2148','Fall 2014','2014-08-21','2014-12-19'),
('2152','Spring 2015','2015-01-13','2015-05-15'),
('2155','Summer 2015','2015-05-26','2015-08-14'),
('2158','Fall 2015','2015-08-19','2015-12-18'),
('2162','Spring 2016','2016-01-12','2016-05-13'),
('2165','Summer 2016','2016-05-23','2016-08-12'),
('2168','Fall 2016','2016-08-17','2016-12-16'),
('2172','Spring 2017','2017-01-10','2017-05-12'),
('2175','Summer 2017','2017-05-22','2017-08-11'),
('2178','Fall 2017','2017-08-16','2017-12-15'),
('2182','Spring 2018','2018-01-09','2018-05-11'),
('2185','Summer 2018','2018-05-21','2018-08-10'),
('2188','Fall 2018','2018-08-15','2018-12-14'),
('2192','Spring 2019','2019-01-15','2019-05-17'),
('2195','Summer 2019','2019-05-28','2019-08-16'),
('2198','Fall 2019','2019-08-21','2019-12-20'),
('2202','Spring 2020','2020-01-14','2020-05-15'),
('2205','Summer 2020','2020-05-26','2020-08-14'),
('2208','Fall 2020','2020-08-19','2020-12-18'),
('2212','Spring 2021','2021-01-12','2021-05-14'),
('2215','Summer 2021','2021-05-24','2021-08-13'),
('2218','Fall 2021','2021-08-18','2021-12-17'),
('2222','Spring 2022','2022-01-11','2022-05-13'),
('2225','Summer 2022','2022-05-23','2022-08-12'),
('2228','Fall 2022','2022-08-17','2022-12-16'),
('2232','Spring 2023','2023-01-10','2023-05-12'),
('2235','Summer 2023','2023-05-22','2023-08-11'),
('2238','Fall 2023','2023-08-16','2023-12-15'),
('2242','Spring 2024','2024-01-09','2024-05-10'),
('2245','Summer 2024','2024-05-20','2024-08-09'),
('2248','Fall 2024','2024-08-21','2024-12-06'),
('2252','Spring 2025','2025-01-10','2025-05-01'),
('2255','Summer 2025','2025-05-26','2025-08-01'),
('2258','Fall 2025','2025-08-20','2025-12-12'),
('2262','Spring 2026','2026-01-13','2026-05-15'),
('2265','Summer 2026','2026-05-26','2026-08-14'),
('2268','Fall 2026','2026-08-19','2026-12-18'),
('2272','Spring 2027','2027-01-12','2027-05-14'),
('2275','Summer 2027','2027-05-24','2027-08-13'),
('2278','Fall 2027','2027-08-18','2027-12-17'),
('2282','Spring 2028','2028-01-11','2028-05-12'),
('2285','Summer 2028','2028-05-22','2028-08-11'),
('2288','Fall 2028','2028-08-16','2028-12-15'),
('2292','Spring 2029','2029-01-09','2029-05-11'),
('2295','Summer 2029','2029-05-21','2029-08-10');

DROP SCHEMA IF EXISTS boac_advising_asc cascade;

CREATE SCHEMA boac_advising_asc;

CREATE TABLE boac_advising_asc.students (
    sid VARCHAR,
    active BOOLEAN NOT NULL
);

INSERT INTO boac_advising_asc.students
(sid, active)
VALUES
('3000000012',TRUE),
('3000000013',TRUE);
