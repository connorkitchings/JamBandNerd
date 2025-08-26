# Python: Insert data

## Parameters

*   **`json`** (Required): The values to insert. Pass a `dict` to insert a single row or a `list` to insert multiple rows.[1]
*   **`count`** (Optional): The property to use to get the count of rows returned.[1]
*   **`returning`** (Optional): Either 'minimal' or 'representation'. Defaults to 'representation'.[1]
*   **`default_to_null`** (Optional): Make missing fields default to `null`. Otherwise, use the default value for the column. Only applies for bulk inserts.[1]