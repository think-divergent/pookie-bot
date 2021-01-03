if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <old_name> <new_name>"
    exit
fi
OLD_NAME=$1
NEW_NAME=$2
find $OLD_NAME -type f|xargs -L 1 -- sed -i'.backup' -e "s/${OLD_NAME}/${NEW_NAME}/g"
mv $OLD_NAME $NEW_NAME
find $NEW_NAME -name *.backup|xargs -L 1 rm 
