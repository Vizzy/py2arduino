#include <stdlib.h>
#include <iostream>

// using namespace std;

template <class T>
class List;

template <class T>
class Container
{
public:
	bool _contains(T element)
	{
		for (int i = 0; i < length; ++i)
		{
			if (elts[i] == element)
				return true;
		}
		return false;
	}
	
protected:
	T *elts;
	int length;
};

template <class T>
class Tuple : public Container<T>
{
public:
	Tuple(T *elements, int n)
	{
			this->elts = (T *) malloc(sizeof(T) * n);

			for (int i = 0; i < n; ++i)
			{
				this->elts[i] = elements[i];
			}

			this->length = n;
	}

	int count()
	{
		return this->length;
	}

	int index(T elt)
	{
		for (int i = 0; i < this->length; ++i)
		{
			if (this->elts[i] == elt)
				return i;
		}

		return -1;
	}

	int operator[] (const int n)
	{
	    return this->elts[n];
	}
};

template <class T>
class Node
{
	friend class List<T>;
public:
	Node() : next(NULL){}

	T data;
	Node *next;
};

template <class T>
class List
{
public:
	List()
	{
		length = 0;
	}

	bool contains(T elem)
	{
		Node<T> *cur_elem = &root_elem;
		while(cur_elem != NULL)
		{
			if (cur_elem->data == elem)
			{
				return true;
			}
			cur_elem = cur_elem->next;
		}
		return false;
	}

	int index(T elem)
	{
		if (length > 0)
		{
			Node<T> *cur_elem = &root_elem;
			int ind = 0;

			while (cur_elem != NULL)
			{
				if (cur_elem->data == elem)
				{
					return ind;
				}
				else
				{
					cur_elem = cur_elem->next;
					ind++;
				}
			}

			// if the loop runs out
			return -1;
		}
		else
		{
			return -1;
		}
	}

	void append(T elem)
	{
		Node<T> new_elem;
		new_elem.data = elem;

		if (length == 0)
		{
			root_elem = new_elem;
		}
		else
		{
			Node<T> *cur_elem = get_current_elem();
			cur_elem->next = new Node<T>(new_elem);
		}

		length++;
	}

	void remove(const T elem)
	{
		if (length > 0)
		{
			int ind = index(elem);

			if (ind == -1)
			{
				return;
			}

			if (ind == 0)
			{
				Node<T> *root = &root_elem;
				root = root->next;
			}
			else if (ind > 0)
			{
				int count = 1;
				Node<T> *cur_elem = &root_elem;

				while (count < ind)
				{
					cur_elem = cur_elem->next;
				}

				cur_elem->next = cur_elem->next->next;
			}
		}

		length--;
	}

	int operator[] (const int ind)
	{
		Node<T> *theElem = get_elem_at_index(ind);
		return theElem->data;
	}

	void print()
	{
		std::cout << "[";

		for (int i = 0; i < length; ++i)
		{
			Node<T> *elem = get_elem_at_index(i);
			std::cout << elem->data; 

			if (i + 1 < length)
			{
				std::cout << ", ";
			}
		}

		std::cout << "]\n";
	}

	int length;
	Node<T> root_elem;
	typedef T type;

private:
	Node<T> *get_current_elem()
	{
		Node<T> *cur_elem = &root_elem;
		while(cur_elem->next != NULL)
		{
			cur_elem = cur_elem->next;
		}
		return cur_elem;
	}

	Node<T> *get_elem_at_index(const int ind)
	{
		if (length > 0 && ind < length)
		{
			Node<T> *cur_elem = &root_elem;
			int count = 0;

			while (count < ind)
			{
				cur_elem = cur_elem->next;
				count++;
			}

			return cur_elem;
		}
		else
		{
			return NULL;
		}
	}

protected:
	T *as_array()
	{
		T *arr = malloc(length * sizeof(T));

		for (int i = 0; i < length; i++)
		{
			arr[i] = this[i];
		}

		return arr;
	}
};