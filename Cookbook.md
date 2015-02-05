Cookbook
========


Change Newline Delimited JSON Field Names
-----------------------------------------

Example fieldmap:

```json
{
  "field1": "FIELD1",
  "field2": "something-else"
}
```

Command:

``` console
$ pyin -i newline.json \
      -im module.FIELD_MAP \
      -im newlinejson \
      -r newlinejson.Reader \
      -w newlinejson.Writer \
       "{module.FIELD_MAP[key]: val for key, val in line.iteritems() if key in module.FIELD_MAP}"
```
