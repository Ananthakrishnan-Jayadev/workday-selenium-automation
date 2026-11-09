"""Application Questions (verified: CIBC run 2026-11-09, applyFlowPrimaryQuestionsPage).

Each question is a [data-automation-id="formField-<32 hex id>"] container with a <fieldset><legend>
holding the question text (in a richText div) and one control: a dropdown button, a checkbox group
([data-automation-id$="-CheckboxGroup"]), radios, a text box or a textarea. The hex ids differ per
company and per question, so questions are found by structure and matched by their text.
"""
from locators import aid

PRIMARY = aid("applyFlowPrimaryQuestionsPage")
SECONDARY = aid("applyFlowSecondaryQuestionsPage")
ROOT_CSS = ('[data-automation-id="applyFlowPrimaryQuestionsPage"], '
            '[data-automation-id="applyFlowSecondaryQuestionsPage"]')

# Top-level question containers inside a questionnaire root, with their text and required flag.
JS_QUESTIONS = """
const root = document.querySelector(arguments[0]);
if (!root) return [];
const fields = [...root.querySelectorAll('[data-automation-id^="formField-"]')]
    .filter(f => !f.parentElement.closest('[data-automation-id^="formField-"]'));
return fields.map(f => {
    const legend = f.querySelector('legend') || f.querySelector('label');
    const raw = (legend ? legend.innerText : f.innerText || '').trim();
    const required = /\\*\\s*$/.test(raw) || !!f.querySelector('[aria-required="true"]');
    return [f.getAttribute('data-automation-id'), raw.replace(/\\s*\\*\\s*$/, '').replace(/\\s+/g, ' '), required];
});
"""

# Voluntary Disclosures (verified: CIBC run 2026-11-09). On CIBC it only holds the required
# "I agree to the above" terms checkbox (formField-acceptTermsAndAgreements, label instead of legend);
# US tenants put gender / ethnicity / veteran questions here.
DISCLOSURES_ROOT_CSS = '[data-automation-id="applyFlowVoluntaryDisclosuresPage"]'

# Self Identify (disability form, mostly US tenants). Unverified: CIBC has no such step.
SELF_IDENTIFY_ROOT_CSS = '[data-automation-id="applyFlowSelfIdentifyPage"], [data-automation-id="selfIdentificationPage"]'
