#!/bin/bash

OUTPUT=$(python manage.py migrate --noinput)
RETVAL=$?
if [[ $RETVAL -ne 0 ]]; then
    echo "An error occurred: migration failed"
    echo "$OUTPUT"
    exit $RETVAL 
fi

OUTPUT=$(python manage.py collectstatic --noinput)
RETVAL=$?
if [[ $RETVAL -ne 0 ]]; then
    echo "An error occurred: collectstatic failed"
    echo "$OUTPUT"
    exit $RETVAL 
fi

# Create superuser and capture the output and return status
OUTPUT=$(python manage.py createsuperuser --noinput 2>&1)
RETVAL=$?

# Check if the output contains a specific error message
if echo "$OUTPUT" | grep -q "That username is already taken."; then
    echo "The username is already taken. Ignoring this error."
    exit 0
elif [[ $RETVAL -ne 0 ]]; then
    echo "An error occurred: createsuperuser failed"
    echo "$OUTPUT"
    exit $RETVAL  # Exit with the original error code if a different error occurred
fi

exit 0
