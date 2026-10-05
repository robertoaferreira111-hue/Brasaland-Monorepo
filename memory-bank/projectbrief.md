# Brasaland project brief

Business facts below are taken from the root `CONTEXT.md` briefing. Do not add company facts from elsewhere.

## Business description

Brasaland is a grilled-food restaurant chain founded in 2008 in Medellín, Colombia. It grew from one family-run location into 14 company-owned restaurants in two countries: Colombia and the United States (Florida). The company employs about 115 people and generates about 6 million dollars in annual revenue.

Headquarters are in Medellín. A commercial and operations office in Miami coordinates the Florida locations. Mariana Restrepo, daughter of the founder, has been CEO since 2019. She brought the business to the US market.

The brand commitments in the briefing are: food that tastes the same in Medellín or Miami, a service experience that feels warm and consistent, and a kitchen that moves fast.

The company is profitable and has a loyal customer base in both markets. It is still run with tools built for a single local restaurant.

## Brasaland Digital

Mariana created an internal team called Brasaland Digital. Its mandate is to build the tools, systems, and automations that let Brasaland operate like a modern company without losing what has always made it good.

Work in this repository is for that team.

## The problem this solves

A 14-location, two-country operation is being managed with single-restaurant tools. The briefing states the visible consequences:

- Ingredient orders go out by WhatsApp or phone, with no inventory data, so some locations overstock and others stock out.
- The loyalty programme, Brasa Points, runs on physical stamp cards that customers lose. The cards produce no customer data. About 60% of customers do not use them.
- There is no real-time view of what is happening at a location.
- Leadership cannot answer basic questions without phone calls. Weekly PDF reports arrive on Tuesday mornings.
- The public website is from 2019, accepts no online orders, and the app has a 2.8 app store rating.
- Each country has a different point-of-sale system. There is no internal API, no consolidated data, and no telemetry. Spreadsheets are doing the work of management systems.

Competitors are gaining ground with digital ordering, data-driven marketing, and operational dashboards.

## Department owners and forward work

Names, roles, and needs are only those stated in `CONTEXT.md`.

### Restaurant Operations

Director: Felipe Guerrero. Supervisors oversee all 14 locations. Each location runs its own kitchen, staff, and supply orders with little visibility from headquarters. Shift reports are paper or Excel and go to HR weekly.

Forward work stated in the briefing:

- Real-time sales dashboard per location, in COP and USD.
- Ingredient ordering based on historical sales and current stock.
- Alerts when a location shows no sales during opening hours.

### Procurement and Suppliers

Manager: Lucía Fernández. About 20 suppliers, split between Colombia and Florida, cover meat, vegetables, sauces, beverages, packaging, and cleaning products. Negotiation is by email and Excel, separately in each market. Price changes show up when the invoice arrives. Purchasing data is not consolidated.

Forward work stated in the briefing:

- A supplier platform with price history and alerts.
- Consolidated purchasing visibility for central negotiations across both markets.

### Marketing and Digital Experience

Manager: Camila Ospina. The team owns the website, social media, the loyalty programme, and campaigns. The two markets are culturally different, and the company has almost no data on who its customers are.

Forward work stated in the briefing:

- A digital loyalty and ordering app.
- A customer CRM with order history and preferences.
- A personalisation engine that suggests products from behaviour.

### People and Culture

Manager: Ashley Turner, in Miami. The function covers contracts, schedules, onboarding, and day-to-day HR for about 115 people in two labour markets. Most HR work is email and Excel. Kitchen onboarding is manual, and kitchen staff turn over frequently.

Forward work stated in the briefing:

- An internal HR portal for holiday requests and absence management.
- An automated onboarding flow.
- An HR KPI dashboard for turnover, absenteeism, and vacancy fill times, segmented by country.

### Training and Quality Standards

Manager: Jake Morrison, in Miami. Every location must follow the same recipes, preparation, and presentation. Materials sit in a shared Google Drive that is hard to navigate. Recipe or procedure changes take days to reach all 14 locations and often cause confusion. The briefing says multilingual support (Spanish and English) is optional but highly recommended, starting from one base language.

Forward work stated in the briefing:

- A training platform with a searchable recipe catalogue.
- A structured onboarding path for new staff.
- A system that pushes recipe updates to all locations at the same time.

### Technology

CTO: Nicolás Park, in Medellín, with a small team. The briefing describes the current company technology as a static website, an outdated app, a different POS terminal in each country with no integration, and spreadsheets. Nicolás is mandated to build the digital platform from near-zero.

Forward work stated in the briefing:

- A central API covering locations, menus, sales, customers, and suppliers.
- Real-time telemetry from each location.
- A data pipeline feeding the operations, marketing, and finance dashboards.

### Executive leadership

CEO: Mariana Restrepo. She cannot answer, in real time, how much the chain sold this week in Florida or which location has the highest average ticket this month.

Forward work stated in the briefing:

- An executive dashboard with total chain sales in USD and COP.
- An AI assistant she can query in natural language.
- An automated weekly report generated and sent every Monday at 7am.
