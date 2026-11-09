Feature: Apply to a Workday job
  Fill a Workday application from the Excel workbook and stop before submitting.

  Run one job:     behave -D url="https://<company>.wd3.myworkdayjobs.com/.../job/..."
  Or a Jobs row:   behave -D row=2

  Scenario: Fill a Workday application
    Given the job to apply for is loaded
    And the applicant data is loaded from Excel
    When I open the job posting
    And I start the application manually
    And I sign in with the account for this company
    And I complete the "My Information" page
    And I complete the "My Experience" page
    And I complete the "Application Questions" page
    Then I should be on the "Voluntary Disclosures" page
