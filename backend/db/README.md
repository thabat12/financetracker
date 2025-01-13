here the database models object will be stored. when deploying services, certain python modules will
be selected for their corresponding tasks. like for example, batch scripts will take the backend/batch
and backend/db folders, but the backend/api folder will not be used.

setup instructions

```bash
$ conda create -n financetracker python=3.11
$ conda activate financetracker
$ pip install -r requirements.txt
```


setting up the financetracker database:
