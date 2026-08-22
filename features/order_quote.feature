Feature: Quote an order
  As a delivery team
  I want an executable pricing policy
  So that edge cases are agreed before AI-generated code is accepted

  Scenario: A standard order pays regular shipping
    Given a standard member has an order subtotal of 2000 cents
    When the order is quoted
    Then the total is 2500 cents

  Scenario: Discounts are applied before the free-shipping decision
    Given a premium member has an order subtotal of 6000 cents
    And the coupon discount is 10 percent
    When the order is quoted
    Then the coupon discount is 600 cents
    And the membership discount is 270 cents
    And shipping is free
    And the total is 5130 cents

  Scenario: Express shipping is never free
    Given a standard member has an order subtotal of 6000 cents
    And express shipping is requested
    When the order is quoted
    Then shipping costs 1200 cents
    And the total is 7200 cents
