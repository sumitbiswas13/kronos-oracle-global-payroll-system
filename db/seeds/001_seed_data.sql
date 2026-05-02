-- ============================================================
-- Global Payroll System — Seed Data
-- Countries: US, GB, IN, AU
-- ============================================================

-- ── COUNTRIES ────────────────────────────────────────────────
INSERT INTO GPS_COUNTRIES VALUES ('US', 'United States',  'USD', '01-01', 'BIWEEKLY', 'Y', SYSTIMESTAMP);
INSERT INTO GPS_COUNTRIES VALUES ('GB', 'United Kingdom', 'GBP', '04-06', 'MONTHLY',  'Y', SYSTIMESTAMP);
INSERT INTO GPS_COUNTRIES VALUES ('IN', 'India',          'INR', '04-01', 'MONTHLY',  'Y', SYSTIMESTAMP);
INSERT INTO GPS_COUNTRIES VALUES ('AU', 'Australia',      'AUD', '07-01', 'MONTHLY',  'Y', SYSTIMESTAMP);

-- ── EMPLOYEE TYPES ───────────────────────────────────────────
INSERT INTO GPS_EMPLOYEE_TYPES VALUES ('FULLTIME',  'Full-Time Employee',  'Y', 'Y', 'N', 'Permanent salaried employee with full benefits', 'Y');
INSERT INTO GPS_EMPLOYEE_TYPES VALUES ('HOURLY',    'Hourly Employee',     'N', 'Y', 'Y', 'Paid per hour worked, overtime eligible', 'Y');
INSERT INTO GPS_EMPLOYEE_TYPES VALUES ('PARTTIME',  'Part-Time Employee',  'N', 'Y', 'N', 'Part-time hourly or prorated salary', 'Y');
INSERT INTO GPS_EMPLOYEE_TYPES VALUES ('CONTRACT',  'Contractor',          'N', 'N', 'N', 'Fixed-term or project-based contractor', 'Y');
INSERT INTO GPS_EMPLOYEE_TYPES VALUES ('INTERN',    'Intern',              'N', 'N', 'N', 'Internship, may be paid or unpaid', 'Y');

-- ── US STATES ────────────────────────────────────────────────
INSERT INTO GPS_STATES (COUNTRY_CODE, STATE_CODE, STATE_NAME, HAS_STATE_TAX) VALUES ('US', 'CA', 'California',  'Y');
INSERT INTO GPS_STATES (COUNTRY_CODE, STATE_CODE, STATE_NAME, HAS_STATE_TAX) VALUES ('US', 'NY', 'New York',    'Y');
INSERT INTO GPS_STATES (COUNTRY_CODE, STATE_CODE, STATE_NAME, HAS_STATE_TAX) VALUES ('US', 'TX', 'Texas',       'N');
INSERT INTO GPS_STATES (COUNTRY_CODE, STATE_CODE, STATE_NAME, HAS_STATE_TAX) VALUES ('US', 'WA', 'Washington',  'N');
INSERT INTO GPS_STATES (COUNTRY_CODE, STATE_CODE, STATE_NAME, HAS_STATE_TAX) VALUES ('US', 'FL', 'Florida',     'N');
INSERT INTO GPS_STATES (COUNTRY_CODE, STATE_CODE, STATE_NAME, HAS_STATE_TAX) VALUES ('US', 'IL', 'Illinois',    'Y');

-- ── UK REGIONS ───────────────────────────────────────────────
INSERT INTO GPS_STATES (COUNTRY_CODE, STATE_CODE, STATE_NAME, HAS_STATE_TAX) VALUES ('GB', 'ENG', 'England',          'N');
INSERT INTO GPS_STATES (COUNTRY_CODE, STATE_CODE, STATE_NAME, HAS_STATE_TAX) VALUES ('GB', 'SCT', 'Scotland',         'Y');
INSERT INTO GPS_STATES (COUNTRY_CODE, STATE_CODE, STATE_NAME, HAS_STATE_TAX) VALUES ('GB', 'WLS', 'Wales',            'N');
INSERT INTO GPS_STATES (COUNTRY_CODE, STATE_CODE, STATE_NAME, HAS_STATE_TAX) VALUES ('GB', 'NIR', 'Northern Ireland',  'N');

-- ── INDIA STATES ─────────────────────────────────────────────
INSERT INTO GPS_STATES (COUNTRY_CODE, STATE_CODE, STATE_NAME, HAS_STATE_TAX) VALUES ('IN', 'MH', 'Maharashtra', 'N');
INSERT INTO GPS_STATES (COUNTRY_CODE, STATE_CODE, STATE_NAME, HAS_STATE_TAX) VALUES ('IN', 'KA', 'Karnataka',   'N');
INSERT INTO GPS_STATES (COUNTRY_CODE, STATE_CODE, STATE_NAME, HAS_STATE_TAX) VALUES ('IN', 'DL', 'Delhi',       'N');
INSERT INTO GPS_STATES (COUNTRY_CODE, STATE_CODE, STATE_NAME, HAS_STATE_TAX) VALUES ('IN', 'TN', 'Tamil Nadu',  'N');

-- ── AUSTRALIA STATES ─────────────────────────────────────────
INSERT INTO GPS_STATES (COUNTRY_CODE, STATE_CODE, STATE_NAME, HAS_STATE_TAX) VALUES ('AU', 'NSW', 'New South Wales', 'N');
INSERT INTO GPS_STATES (COUNTRY_CODE, STATE_CODE, STATE_NAME, HAS_STATE_TAX) VALUES ('AU', 'VIC', 'Victoria',        'N');
INSERT INTO GPS_STATES (COUNTRY_CODE, STATE_CODE, STATE_NAME, HAS_STATE_TAX) VALUES ('AU', 'QLD', 'Queensland',      'N');

-- ── LEAVE TYPES ──────────────────────────────────────────────
INSERT INTO GPS_LEAVE_TYPES VALUES ('ANNUAL',    'Annual Leave',         NULL, 20,  'Y', 'Y', 'Y');
INSERT INTO GPS_LEAVE_TYPES VALUES ('SICK',      'Sick Leave',           NULL, 10,  'Y', 'N', 'Y');
INSERT INTO GPS_LEAVE_TYPES VALUES ('MATERNITY', 'Maternity Leave',      NULL, 90,  'Y', 'N', 'Y');
INSERT INTO GPS_LEAVE_TYPES VALUES ('PATERNITY', 'Paternity Leave',      NULL, 10,  'Y', 'N', 'Y');
INSERT INTO GPS_LEAVE_TYPES VALUES ('UNPAID',    'Unpaid Leave',         NULL, 0,   'N', 'N', 'Y');
INSERT INTO GPS_LEAVE_TYPES VALUES ('PUBLIC',    'Public Holiday',       NULL, 0,   'Y', 'N', 'Y');
INSERT INTO GPS_LEAVE_TYPES VALUES ('BEREAVEMENT','Bereavement Leave',   NULL, 5,   'Y', 'N', 'Y');

-- ── DEDUCTION TYPES ──────────────────────────────────────────
INSERT INTO GPS_DEDUCTION_TYPES VALUES ('HEALTH_INS',  'Health Insurance',      'US', 'Y', 'N', 'FIXED',   'Y');
INSERT INTO GPS_DEDUCTION_TYPES VALUES ('DENTAL_INS',  'Dental Insurance',      'US', 'Y', 'N', 'FIXED',   'Y');
INSERT INTO GPS_DEDUCTION_TYPES VALUES ('401K',        '401(k) Contribution',   'US', 'Y', 'N', 'PERCENT', 'Y');
INSERT INTO GPS_DEDUCTION_TYPES VALUES ('PENSION_UK',  'UK Workplace Pension',  'GB', 'Y', 'N', 'PERCENT', 'Y');
INSERT INTO GPS_DEDUCTION_TYPES VALUES ('PF_INDIA',    'Provident Fund (India)','IN', 'Y', 'Y', 'PERCENT', 'Y');
INSERT INTO GPS_DEDUCTION_TYPES VALUES ('SUPER_AU',    'Superannuation (AU)',   'AU', 'N', 'Y', 'PERCENT', 'Y');
INSERT INTO GPS_DEDUCTION_TYPES VALUES ('UNION_DUES',  'Union Dues',            NULL, 'N', 'N', 'FIXED',   'Y');

COMMIT;
