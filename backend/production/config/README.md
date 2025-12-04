# BAIS Configuration

This directory contains configuration files for BAIS.

## Demo Businesses Configuration

The `demo_businesses.json` file controls which businesses are automatically loaded as demos.

### Configuration Structure

```json
{
  "demo_businesses": [
    {
      "enabled": true,
      "customer_file": "BusinessName_BAIS_Submission.json",
      "description": "Description of the demo business"
    }
  ],
  "auto_load_on_startup": true,
  "auto_load_when_database_empty": true
}
```

### Fields

- **demo_businesses**: Array of demo business configurations
  - **enabled**: (boolean) Whether this business should be loaded
  - **customer_file**: (string) Filename in the `customers/` directory
  - **description**: (string) Human-readable description of the business

- **auto_load_on_startup**: (boolean) Load demo businesses when server starts
- **auto_load_when_database_empty**: (boolean) Load demo businesses if database is empty

### Adding a New Demo Business

1. Add your business JSON file to the `customers/` directory
2. Add an entry to `demo_businesses` array:
   ```json
   {
     "enabled": true,
     "customer_file": "YourBusiness_BAIS_Submission.json",
     "description": "Your Business - Demo for [industry]"
   }
   ```
3. Restart the server

### Disabling a Demo Business

Set `"enabled": false` for that business entry.

### No Hard-Coding Required

BAIS is designed to be **business-agnostic**. All business-specific data should come from:
1. Configuration files (like this)
2. Database registrations
3. Customer submission files

**Never** hard-code business names, service names, or business-specific logic in the codebase.
